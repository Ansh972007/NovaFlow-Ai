import JSEncrypt from "jsencrypt";
import client, { clearAuthTokens, storeAuthTokens } from "./client";

let userCache = null;
let userCacheAt = 0;
const USER_CACHE_MS = 20000;

export async function getPublicKey() {
  return client.get("/user/public_key");
}

export async function encryptPassword(password) {
  const res = await getPublicKey();
  const publicKey = typeof res === "string" ? res : res?.public_key;

  if (!publicKey) {
    throw new Error("Could not load encryption key from NovaFlow API");
  }

  const encrypt = new JSEncrypt();
  encrypt.setPublicKey(publicKey);
  const encrypted = encrypt.encrypt(password);
  if (!encrypted) {
    throw new Error("Password encryption failed");
  }
  return encrypted;
}

export async function login(userName, password) {
  const encryptedPassword = await encryptPassword(password);
  const data = await client.post("/user/login", {
    user_name: userName,
    password: encryptedPassword,
  });
  storeAuthTokens(data);
  clearUserCache();
  return data;
}

export async function register(userName, password) {
  const encryptedPassword = await encryptPassword(password);
  const data = await client.post("/user/regist", {
    user_name: userName,
    password: encryptedPassword,
  });
  storeAuthTokens(data);
  clearUserCache();
  return data;
}

export async function getUserInfo(options = {}) {
  const { fresh = false } = options;
  if (!fresh && userCache && Date.now() - userCacheAt < USER_CACHE_MS) {
    return userCache;
  }
  const data = await client.get("/user/info");
  userCache = data;
  userCacheAt = Date.now();
  return data;
}

export function clearUserCache() {
  userCache = null;
  userCacheAt = 0;
}

export async function changePassword(currentPassword, newPassword) {
  const [current_password, new_password] = await Promise.all([
    encryptPassword(currentPassword),
    encryptPassword(newPassword),
  ]);
  return client.post("/user/password", { current_password, new_password });
}

export async function getLdapStatus() {
  return client.get("/auth/ldap/status");
}

export async function logout() {
  clearUserCache();
  const refresh_token =
    typeof window !== "undefined" ? localStorage.getItem("nf_refresh_token") || "" : "";
  try {
    await client.post("/user/logout", { refresh_token });
  } catch {
    /* still clear local session */
  }
  clearAuthTokens();
}
