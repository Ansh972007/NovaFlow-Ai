import base64
import secrets
import zlib
from datetime import datetime, timezone
from urllib.parse import quote, urlencode
from xml.etree import ElementTree as ET

from app.config import (
    FRONTEND_URL,
    OAUTH_REDIRECT_BASE,
    SAML_IDP_CERT,
    SAML_IDP_ENTITY_ID,
    SAML_IDP_SSO_URL,
    SAML_SP_ENTITY_ID,
)


def saml_enabled() -> bool:
    return bool(SAML_IDP_SSO_URL.strip() and SAML_IDP_ENTITY_ID.strip())


def saml_status() -> dict:
    return {
        "enabled": saml_enabled(),
        "idp_entity_id": SAML_IDP_ENTITY_ID if saml_enabled() else "",
        "sp_entity_id": SAML_SP_ENTITY_ID if saml_enabled() else "",
    }


def _acs_url() -> str:
    base = OAUTH_REDIRECT_BASE.rstrip("/")
    return f"{base}/api/v1/auth/saml/acs"


def sp_metadata_xml() -> str:
    acs = _acs_url()
    entity = SAML_SP_ENTITY_ID or "novaflow-ai"
    return f"""<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{entity}">
  <SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="false"
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


def parse_saml_response(saml_response_b64: str) -> dict | None:
    if not saml_response_b64:
        return None
    try:
        raw = base64.b64decode(saml_response_b64)
        root = ET.fromstring(raw)
    except Exception:
        return None

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
