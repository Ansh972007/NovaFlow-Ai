import base64
import hashlib
import secrets
import zlib
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode
from xml.etree import ElementTree as ET

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from app.config import (
    FRONTEND_URL,
    OAUTH_REDIRECT_BASE,
    SAML_IDP_CERT,
    SAML_IDP_ENTITY_ID,
    SAML_IDP_SSO_URL,
    SAML_SP_ENTITY_ID,
)

NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def saml_enabled() -> bool:
    return bool(SAML_IDP_SSO_URL.strip() and SAML_IDP_ENTITY_ID.strip())


def saml_status() -> dict:
    return {
        "enabled": saml_enabled(),
        "idp_entity_id": SAML_IDP_ENTITY_ID if saml_enabled() else "",
        "sp_entity_id": SAML_SP_ENTITY_ID if saml_enabled() else "",
        "signature_verification": bool(SAML_IDP_CERT.strip()),
    }


def _acs_url() -> str:
    base = OAUTH_REDIRECT_BASE.rstrip("/")
    return f"{base}/api/v1/auth/saml/acs"


def sp_metadata_xml() -> str:
    acs = _acs_url()
    entity = SAML_SP_ENTITY_ID or "novaflow-ai"
    return f"""<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{entity}">
  <SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true"
    protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</NameIDFormat>
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="{acs}" index="1"/>
  </SPSSODescriptor>
</EntityDescriptor>"""


def build_saml_login_redirect() -> str | None:
    if not saml_enabled():
        return None
    req_id = f"_nf{secrets.token_hex(16)}"
    instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entity = SAML_SP_ENTITY_ID or "novaflow-ai"
    acs = _acs_url()
    xml = f"""<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
  xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
  ID="{req_id}" Version="2.0" IssueInstant="{instant}"
  Destination="{SAML_IDP_SSO_URL}"
  AssertionConsumerServiceURL="{acs}"
  ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
  <saml:Issuer>{entity}</saml:Issuer>
  <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" AllowCreate="true"/>
</samlp:AuthnRequest>"""
    compressed = zlib.compress(xml.encode("utf-8"))[2:-4]
    encoded = base64.b64encode(compressed).decode("ascii")
    params = urlencode({"SAMLRequest": encoded, "RelayState": FRONTEND_URL.rstrip("/")})
    join = "&" if "?" in SAML_IDP_SSO_URL else "?"
    return f"{SAML_IDP_SSO_URL}{join}{params}"


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_x509_cert(pem_or_b64: str):
    raw = (pem_or_b64 or "").strip()
    if not raw:
        return None
    if "BEGIN CERTIFICATE" not in raw:
        raw = f"-----BEGIN CERTIFICATE-----\n{raw}\n-----END CERTIFICATE-----"
    try:
        cert = x509.load_pem_x509_certificate(raw.encode("utf-8"))
        return cert.public_key()
    except Exception:
        try:
            return load_pem_public_key(raw.encode("utf-8"))
        except Exception:
            return None


def _parse_saml_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _validate_conditions(root: ET.Element) -> None:
    entity = SAML_SP_ENTITY_ID or "novaflow-ai"
    now = datetime.now(timezone.utc)
    skew = timedelta(minutes=5)
    for el in root.iter():
        tag = _local_name(el.tag)
        if tag == "Audience" and el.text:
            aud = el.text.strip()
            if aud and aud != entity and entity not in aud:
                raise ValueError("SAML Audience mismatch")
        if tag == "Conditions":
            nb = _parse_saml_time(el.get("NotBefore") or "")
            na = _parse_saml_time(el.get("NotOnOrAfter") or "")
            if nb and now < nb - skew:
                raise ValueError("SAML assertion not yet valid")
            if na and now > na + skew:
                raise ValueError("SAML assertion expired")
        if tag == "StatusCode":
            val = el.get("Value") or ""
            if val and not val.endswith(":Success"):
                raise ValueError("SAML response status not successful")


def _verify_xml_signature(root: ET.Element, public_key) -> None:
    sig = None
    for el in root.iter():
        if _local_name(el.tag) == "Signature":
            sig = el
            break
    if sig is None:
        raise ValueError("SAML response is not signed")

    signed_info = None
    sig_value_el = None
    for child in sig:
        ln = _local_name(child.tag)
        if ln == "SignedInfo":
            signed_info = child
        elif ln == "SignatureValue":
            sig_value_el = child

    if signed_info is None or sig_value_el is None or not sig_value_el.text:
        raise ValueError("Invalid SAML signature structure")

    canonical = ET.tostring(signed_info, encoding="utf-8")
    digest = hashlib.sha256(canonical).digest()
    signature = base64.b64decode(sig_value_el.text.strip())
    public_key.verify(signature, digest, padding.PKCS1v15(), hashes.SHA256())


def verify_and_parse_saml_response(saml_response_b64: str) -> dict | None:
    if not saml_response_b64:
        return None
    try:
        raw = base64.b64decode(saml_response_b64)
        root = ET.fromstring(raw)
    except Exception:
        return None

    try:
        _validate_conditions(root)
        cert_key = _parse_x509_cert(SAML_IDP_CERT)
        if cert_key:
            _verify_xml_signature(root, cert_key)
    except ValueError:
        return None
    except Exception:
        if SAML_IDP_CERT.strip():
            return None

    return _extract_saml_profile(root)


def _extract_saml_profile(root: ET.Element) -> dict | None:
    name_id = ""
    email = ""
    display_name = ""

    for el in root.iter():
        tag = _local_name(el.tag)
        if tag == "NameID" and el.text:
            name_id = (el.text or "").strip()
        if tag == "Attribute":
            attr_name = (el.get("Name") or el.get("name") or "").lower()
            val = ""
            for child in el:
                if _local_name(child.tag) == "AttributeValue" and child.text:
                    val = child.text.strip()
                    break
            if "email" in attr_name and val:
                email = val
            if attr_name in {"displayname", "name", "cn", "givenname"} and val:
                display_name = val

    username = name_id.split("@")[0] if name_id else ""
    if not username and email:
        username = email.split("@")[0]
    if not username:
        return None

    return {
        "username": username[:80],
        "email": (email or name_id if "@" in name_id else "")[:255],
        "name": (display_name or username)[:80],
    }


def parse_saml_response(saml_response_b64: str) -> dict | None:
    """Parse SAML response; verifies signature when SAML_IDP_CERT is configured."""
    if SAML_IDP_CERT.strip():
        return verify_and_parse_saml_response(saml_response_b64)
    try:
        raw = base64.b64decode(saml_response_b64)
        root = ET.fromstring(raw)
        _validate_conditions(root)
        return _extract_saml_profile(root)
    except Exception:
        return None
