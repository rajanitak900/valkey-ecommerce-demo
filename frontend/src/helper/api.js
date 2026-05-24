const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function getToken() {
  return window.localStorage.getItem("access_token");
}

function getHeaders(auth = false) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

async function request(path, options = {}) {
  const { method = "GET", body, auth = false } = options;
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: getHeaders(auth),
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let error = { detail: response.statusText };
    try {
      error = await response.json();
    } catch (e) {
      // ignore
    }
    throw new Error(error.detail || error.message || response.statusText);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const getProducts = () => request("/api/products");
export const addCartItem = (productId, quantity = 1) =>
  request("/api/cart/items", {
    method: "POST",
    body: { product_id: productId, quantity },
    auth: true,
  });
export const getCart = () => request("/api/cart", { auth: true });
export const updateCartItem = (productId, quantity) =>
  request(`/api/cart/items/${productId}`, {
    method: "PATCH",
    body: { product_id: productId, quantity },
    auth: true,
  });
export const removeCartItem = (productId) =>
  request(`/api/cart/items/${productId}`, { method: "DELETE", auth: true });
export const login = (email, password) =>
  request("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
export const register = (name, email, password) =>
  request("/api/auth/register", {
    method: "POST",
    body: { full_name: name, email, password },
  });
export const authMe = () => request("/api/auth/me", { auth: true });
export const logout = async () => {
  const token = getToken();
  if (!token) return null;
  const response = await fetch(`${BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error("Logout failed");
  }
  window.localStorage.removeItem("access_token");
  return response.json();
};

export function saveToken(token) {
  if (token) {
    window.localStorage.setItem("access_token", token);
  }
}
