const DEFAULT_BACKEND_URL = "http://localhost:8000";

/**
 * Sends bill image to the backend OCR API.
 * @param {File|Blob} file - The image file to process
 * @param {string} backendUrl - Custom or default API URL
 * @param {string} apiKey - Optional API Key
 * @returns {Promise<Object>} Processed invoice response
 */
export async function processInvoiceImage(file, backendUrl = DEFAULT_BACKEND_URL, apiKey = "") {
  const formData = new FormData();
  formData.append("file", file);

  const headers = {};
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const endpoint = `${backendUrl.replace(/\/+$/, "")}/api/v1/invoice/process`;
  
  const response = await fetch(endpoint, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errorMsg = `Server error (${response.status})`;
    try {
      const errData = await response.json();
      if (errData.detail) {
        errorMsg = errData.detail;
      }
    } catch (_) {}
    throw new Error(errorMsg);
  }

  return await response.json();
}

/**
 * Checks backend health status.
 */
export async function checkBackendHealth(backendUrl = DEFAULT_BACKEND_URL) {
  try {
    const endpoint = `${backendUrl.replace(/\/+$/, "")}/health`;
    const res = await fetch(endpoint);
    return res.ok;
  } catch (_) {
    return false;
  }
}
