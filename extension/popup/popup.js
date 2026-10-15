import { processInvoiceImage, checkBackendHealth } from "../services/api.js";

// DOM Elements
const backendStatusEl = document.getElementById("backendStatus");
const uploadSection = document.getElementById("uploadSection");
const loadingSection = document.getElementById("loadingSection");
const resultsSection = document.getElementById("resultsSection");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const browseBtn = document.getElementById("browseBtn");
const resetBtn = document.getElementById("resetBtn");
const fillErpBtn = document.getElementById("fillErpBtn");
const invoiceForm = document.getElementById("invoiceForm");
const validationBanner = document.getElementById("validationBanner");
const validationIcon = document.getElementById("validationIcon");
const validationText = document.getElementById("validationText");
const validationDetails = document.getElementById("validationDetails");
const toggleSettings = document.getElementById("toggleSettings");
const settingsPanel = document.getElementById("settingsPanel");
const backendUrlInput = document.getElementById("backendUrlInput");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const feedbackToast = document.getElementById("feedbackToast");

let currentBackendUrl = "http://localhost:8000";

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  // Load saved backend URL
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["backendUrl"], (res) => {
      if (res.backendUrl) {
        currentBackendUrl = res.backendUrl;
        backendUrlInput.value = currentBackendUrl;
      }
      checkStatus();
    });
  } else {
    checkStatus();
  }

  setupEventListeners();
});

async function checkStatus() {
  const isOnline = await checkBackendHealth(currentBackendUrl);
  backendStatusEl.className = `status-indicator ${isOnline ? "online" : "offline"}`;
  backendStatusEl.querySelector(".status-text").textContent = isOnline ? "Connected" : "Offline";
}

function showToast(message, type = "success") {
  feedbackToast.textContent = message;
  feedbackToast.className = `toast ${type}`;
  feedbackToast.classList.remove("hidden");
  setTimeout(() => {
    feedbackToast.classList.add("hidden");
  }, 3500);
}

function setupEventListeners() {
  // File upload triggers
  browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag-over");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleImage(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files[0]) {
      handleImage(fileInput.files[0]);
    }
  });

  // Reset / New Scan
  resetBtn.addEventListener("click", () => {
    resultsSection.classList.add("hidden");
    uploadSection.classList.remove("hidden");
    fileInput.value = "";
    invoiceForm.reset();
    clearBadges();
  });

  // Fill ERP Form
  fillErpBtn.addEventListener("click", handleFillERP);

  // Settings
  toggleSettings.addEventListener("click", () => {
    settingsPanel.classList.toggle("hidden");
  });

  saveSettingsBtn.addEventListener("click", () => {
    const val = backendUrlInput.value.trim();
    if (val) {
      currentBackendUrl = val;
      if (chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ backendUrl: val }, () => {
          showToast("Backend URL saved", "success");
          settingsPanel.classList.add("hidden");
          checkStatus();
        });
      }
    }
  });
}

async function handleImage(file) {
  uploadSection.classList.add("hidden");
  loadingSection.classList.remove("hidden");

  try {
    const data = await processInvoiceImage(file, currentBackendUrl);
    displayResults(data);
  } catch (err) {
    loadingSection.classList.add("hidden");
    uploadSection.classList.remove("hidden");
    showToast(err.message || "Failed to process image", "error");
  }
}

function displayResults(data) {
  loadingSection.classList.add("hidden");
  resultsSection.classList.remove("hidden");

  const inv = data.invoice || {};
  const conf = data.confidence || {};
  const val = data.validation || { valid: true, warnings: [], errors: [] };

  // Fill Form fields
  setFieldValue("vendor_name", inv.vendor_name || "", conf.vendor_name);
  setFieldValue("item_name", inv.item_name || "", conf.item_name);
  setFieldValue("invoice_number", inv.invoice_number || "", conf.invoice_number);
  setFieldValue("invoice_date", inv.invoice_date || "", conf.invoice_date);
  setFieldValue("gstin", inv.gstin || "", conf.gstin);
  setFieldValue("subtotal", inv.subtotal !== null ? inv.subtotal : "", conf.subtotal);
  setFieldValue("total", inv.total !== null ? inv.total : "", conf.total);
  setFieldValue("cgst", inv.cgst !== null ? inv.cgst : "", conf.cgst);
  setFieldValue("sgst", inv.sgst !== null ? inv.sgst : "", conf.sgst);
  setFieldValue("igst", inv.igst !== null ? inv.igst : "", conf.igst);
  setFieldValue("description", inv.description || "", conf.description);

  // Display Validation Summary
  updateValidationBanner(val);
}

function setFieldValue(fieldId, value, confidence) {
  const el = document.getElementById(fieldId);
  if (el) {
    el.value = value;
  }
  const badge = document.getElementById(`badge_${fieldId}`);
  if (badge) {
    if (confidence === undefined || confidence === null || confidence === 0) {
      badge.textContent = "";
      badge.className = "conf-badge";
    } else if (confidence >= 0.85) {
      badge.textContent = "🟢 High";
      badge.className = "conf-badge high";
    } else if (confidence >= 0.60) {
      badge.textContent = "🟡 Med";
      badge.className = "conf-badge med";
    } else {
      badge.textContent = "🔴 Low";
      badge.className = "conf-badge low";
    }
  }
}

function clearBadges() {
  document.querySelectorAll(".conf-badge").forEach(b => {
    b.textContent = "";
    b.className = "conf-badge";
  });
}

function updateValidationBanner(val) {
  const hasErrors = val.errors && val.errors.length > 0;
  const hasWarnings = val.warnings && val.warnings.length > 0;

  validationDetails.innerHTML = "";

  if (hasErrors) {
    validationBanner.className = "validation-banner error";
    validationIcon.textContent = "✕";
    validationText.textContent = `${val.errors.length} validation issue(s) detected`;
    
    val.errors.forEach(err => {
      const p = document.createElement("p");
      p.className = "err-item";
      p.textContent = `• ${err}`;
      validationDetails.appendChild(p);
    });
    validationDetails.classList.remove("hidden");
  } else if (hasWarnings) {
    validationBanner.className = "validation-banner warning";
    validationIcon.textContent = "⚠";
    validationText.textContent = `Passed with ${val.warnings.length} warning(s)`;
    
    val.warnings.forEach(warn => {
      const p = document.createElement("p");
      p.className = "warn-item";
      p.textContent = `• ${warn}`;
      validationDetails.appendChild(p);
    });
    validationDetails.classList.remove("hidden");
  } else {
    validationBanner.className = "validation-banner valid";
    validationIcon.textContent = "✓";
    validationText.textContent = "All validation rules passed";
    validationDetails.classList.add("hidden");
  }
}

async function handleFillERP() {
  const formData = {
    vendor_name: (document.getElementById("vendor_name")?.value || "").trim(),
    item_name: (document.getElementById("item_name")?.value || "").trim(),
    invoice_number: (document.getElementById("invoice_number")?.value || "").trim(),
    invoice_date: (document.getElementById("invoice_date")?.value || "").trim(),
    gstin: (document.getElementById("gstin")?.value || "").trim(),
    subtotal: (document.getElementById("subtotal")?.value || "").trim(),
    total: (document.getElementById("total")?.value || "").trim(),
    cgst: (document.getElementById("cgst")?.value || "").trim(),
    sgst: (document.getElementById("sgst")?.value || "").trim(),
    igst: (document.getElementById("igst")?.value || "").trim(),
    description: (document.getElementById("description")?.value || "").trim(),
  };

  try {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!activeTab || !activeTab.id) {
      showToast("No active web page tab found", "error");
      return;
    }

    // Try sending message directly
    chrome.tabs.sendMessage(
      activeTab.id,
      { action: "FILL_ERP_FORM", data: formData },
      async (response) => {
        if (chrome.runtime.lastError) {
          // If content script was not pre-injected (e.g. tab opened before extension load), dynamically inject
          try {
            await chrome.scripting.executeScript({
              target: { tabId: activeTab.id },
              files: ["content/erp.js"]
            });

            // Retry message after injection
            chrome.tabs.sendMessage(
              activeTab.id,
              { action: "FILL_ERP_FORM", data: formData },
              (retryResponse) => {
                if (retryResponse && retryResponse.success && retryResponse.filledFields.length > 0) {
                  showToast(`Filled ${retryResponse.filledFields.length} field(s) in ERP!`, "success");
                } else {
                  showToast("Injected script, but no matching ERP fields found on this tab.", "warning");
                }
              }
            );
          } catch (injectErr) {
            showToast("Cannot autofill: please open a regular ERP webpage tab.", "error");
          }
          return;
        }

        if (response && response.success) {
          const filledCount = response.filledFields.length;
          if (filledCount > 0) {
            showToast(`Filled ${filledCount} field(s) in ERP successfully!`, "success");
          } else {
            showToast("No matching input fields found on this page.", "warning");
          }
        } else {
          showToast("ERP form fields could not be matched.", "error");
        }
      }
    );
  } catch (err) {
    showToast(err.message || "Failed to fill ERP form", "error");
  }
}
