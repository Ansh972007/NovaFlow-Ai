import JSEncrypt from "jsencrypt";
import client from "./client";

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
  return client.post("/user/login", {
    user_name: userName,
    password: encryptedPassword,
  });
}

export async function register(userName, password) {
  const encryptedPassword = await encryptPassword(password);
  return client.post("/user/regist", {
    user_name: userName,
    password: encryptedPassword,
  });
}

export async function getUserInfo() {
  return client.get("/user/info");
}

export async function logout() {
  return client.post("/user/logout");
}
