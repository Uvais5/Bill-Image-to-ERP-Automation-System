/**
 * ERP Content Script - Autofills detected ERP web form fields
 * Supports standard Purchase Invoices, Expense Details Forms (Worksuite, ERPNext, Odoo, SAP, Zoho, Tally)
 * Dispatches framework events (React/Vue/Angular compatible)
 * Human-in-the-loop: Does NOT click Submit!
 */

const FIELD_PATTERNS = {
  item_name: {
    selectors: [
      "#item_name", "#expense_name", "#title", "#item", "#item_title", "#expense_title",
      "input[name='item_name']", "input[name='expense_name']", "input[name='title']", "input[name='item']",
      "input[placeholder*='Keyboard' i]", "input[placeholder*='Item Name' i]", "input[placeholder*='Item' i]"
    ],
    labelKeywords: ["item name", "expense name", "item", "title", "particulars", "product", "expense title"]
  },
  total: {
    selectors: [
      "#price", "#total", "#grand_total", "#total_amount", "#net_amount", "#amount",
      "input[name='price']", "input[name='total']", "input[name='grand_total']", "input[name='total_amount']", "input[name='amount']",
      "input[placeholder*='10000' i]", "input[placeholder*='Price' i]", "input[placeholder*='Total' i]", "input[placeholder*='Amount' i]"
    ],
    labelKeywords: ["price", "total amount", "grand total", "net amount", "total", "amount"]
  },
  invoice_date: {
    selectors: [
      "#purchase_date", "#invoice_date", "#date", "#bill_date", "#expense_date",
      "input[name='purchase_date']", "input[name='invoice_date']", "input[name='date']", "input[name='bill_date']", "input[name='expense_date']",
      "input[type='date']", "input[placeholder*='Date' i]"
    ],
    labelKeywords: ["purchase date", "invoice date", "bill date", "date", "expense date"]
  },
  vendor_name: {
    selectors: [
      "#purchase_from", "#vendor_name", "#vendor", "#supplier", "#supplier_name", "#party_name",
      "input[name='purchase_from']", "input[name='vendor']", "input[name='vendor_name']", "input[name='supplier']", "input[name='party_name']",
      "input[placeholder*='Purchase From' i]", "input[placeholder*='Vendor' i]", "input[placeholder*='Supplier' i]"
    ],
    labelKeywords: ["purchase from", "vendor", "supplier", "party", "merchant", "seller", "billed from"]
  },
  description: {
    selectors: [
      "#description", "#notes", "#remarks", "#expense_description", "#memo",
      "textarea[name='description']", "textarea[name='notes']", "textarea[name='remarks']", "textarea.editor-body",
      "textarea[placeholder*='description' i]", "textarea[placeholder*='notes' i]", "textarea[placeholder*='remarks' i]",
      "div[contenteditable='true']"
    ],
    labelKeywords: ["description", "notes", "remarks", "memo", "details", "particulars breakdown"]
  },
  invoice_number: {
    selectors: [
      "#invoice_number", "#invoice_no", "#bill_no", "#inv_no", "#voucher_no", "#reference_no",
      "input[name='invoice_number']", "input[name='invoice_no']", "input[name='bill_no']", "input[name='voucher_no']", "input[name='reference_no']",
      "input[placeholder*='Invoice No' i]", "input[placeholder*='Bill No' i]", "input[placeholder*='Voucher' i]"
    ],
    labelKeywords: ["invoice no", "invoice number", "bill no", "bill number", "voucher no", "reference no"]
  },
  gstin: {
    selectors: [
      "#gstin", "#gst_number", "#vendor_gstin", "#tax_id",
      "input[name='gstin']", "input[name='gst_number']", "input[name='vendor_gstin']", "input[name='tax_id']",
      "input[placeholder*='GSTIN' i]", "input[placeholder*='GST' i]"
    ],
    labelKeywords: ["gstin", "gst number", "gst no", "tax id", "tin"]
  },
  subtotal: {
    selectors: [
      "#subtotal", "#taxable_amount", "#base_amount", "#sub_total",
      "input[name='subtotal']", "input[name='taxable_amount']", "input[name='base_amount']", "input[name='sub_total']",
      "input[placeholder*='Subtotal' i]", "input[placeholder*='Taxable' i]"
    ],
    labelKeywords: ["subtotal", "taxable amount", "base amount", "sub total"]
  },
  cgst: {
    selectors: [
      "#cgst", "#cgst_amount", "input[name='cgst']", "input[name='cgst_amount']", "input[placeholder*='CGST' i]"
    ],
    labelKeywords: ["cgst", "cgst amount"]
  },
  sgst: {
    selectors: [
      "#sgst", "#sgst_amount", "input[name='sgst']", "input[name='sgst_amount']", "input[placeholder*='SGST' i]"
    ],
    labelKeywords: ["sgst", "sgst amount", "utgst"]
  },
  igst: {
    selectors: [
      "#igst", "#igst_amount", "input[name='igst']", "input[name='igst_amount']", "input[placeholder*='IGST' i]"
    ],
    labelKeywords: ["igst", "igst amount", "integrated tax"]
  }
};

/**
 * Enhanced universal DOM field finder
 */
function findUniversalInput(fieldKey) {
  const pattern = FIELD_PATTERNS[fieldKey];
  if (!pattern) return null;

  // 1. Direct CSS Selector search
  for (const sel of pattern.selectors) {
    const el = document.querySelector(sel);
    if (el && isElementVisible(el)) return el;
  }

  // 2. Search by label text matching
  const labels = Array.from(document.querySelectorAll("label, span.label, div.label"));
  for (const kw of pattern.labelKeywords) {
    const match = labels.find(l => l.textContent.trim().toLowerCase().includes(kw.toLowerCase()));
    if (match) {
      // Check htmlFor
      if (match.htmlFor) {
        const target = document.getElementById(match.htmlFor);
        if (target && isElementVisible(target)) return target;
      }
      // Check nested input
      const nested = match.querySelector("input, select, textarea");
      if (nested && isElementVisible(nested)) return nested;

      // Check next sibling
      let sibling = match.nextElementSibling;
      while (sibling) {
        if (sibling.matches && sibling.matches("input, select, textarea")) return sibling;
        const sub = sibling.querySelector ? sibling.querySelector("input, select, textarea") : null;
        if (sub && isElementVisible(sub)) return sub;
        sibling = sibling.nextElementSibling;
      }

      // Check parent container
      const container = match.closest(".form-group, .form-control, .field, .input-group, div, tr, td");
      if (container) {
        const inputInContainer = container.querySelector("input:not([type='hidden']), select, textarea");
        if (inputInContainer && isElementVisible(inputInContainer)) return inputInContainer;
      }
    }
  }

  // 3. Search by input attributes (placeholder, aria-label, name, id)
  const allInputs = Array.from(document.querySelectorAll("input:not([type='hidden']), textarea, select"));
  for (const input of allInputs) {
    const name = (input.name || "").toLowerCase();
    const id = (input.id || "").toLowerCase();
    const placeholder = (input.placeholder || "").toLowerCase();
    const aria = (input.getAttribute("aria-label") || "").toLowerCase();

    for (const kw of pattern.labelKeywords) {
      const cleanKw = kw.replace(/\s+/g, "");
      if (
        name.includes(cleanKw) ||
        id.includes(cleanKw) ||
        placeholder.includes(kw) ||
        aria.includes(kw)
      ) {
        if (isElementVisible(input)) return input;
      }
    }
  }

  return null;
}

function isElementVisible(el) {
  if (!el) return false;
  const style = window.getComputedStyle(el);
  return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
}

function setNativeValue(element, value) {
  if (!element || value === null || value === undefined) return;

  if (element.tagName === "SELECT") {
    const options = Array.from(element.options);
    const match = options.find(
      opt => opt.value.toLowerCase() === String(value).toLowerCase() ||
             opt.text.toLowerCase().includes(String(value).toLowerCase())
    );
    if (match) {
      element.value = match.value;
    }
  } else if (element.isContentEditable) {
    element.innerText = value;
  } else {
    let formattedValue = value;
    if (element.type === "date" && String(value).includes("/")) {
      const parts = String(value).split("/");
      if (parts.length === 3) {
        formattedValue = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
      }
    }

    const valueSetter = Object.getOwnPropertyDescriptor(element, "value")?.set;
    const prototype = Object.getPrototypeOf(element);
    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;

    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
      prototypeValueSetter.call(element, formattedValue);
    } else if (valueSetter) {
      valueSetter.call(element, formattedValue);
    } else {
      element.value = formattedValue;
    }
  }

  element.dispatchEvent(new Event("focus", { bubbles: true }));
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  element.dispatchEvent(new Event("blur", { bubbles: true }));
}

function highlightElement(el) {
  const originalOutline = el.style.outline;
  const originalTransition = el.style.transition;
  el.style.transition = "outline 0.3s ease, box-shadow 0.3s ease";
  el.style.outline = "2px solid #10b981";
  el.style.boxShadow = "0 0 8px rgba(16, 185, 129, 0.4)";
  setTimeout(() => {
    el.style.outline = originalOutline;
    el.style.boxShadow = "";
    el.style.transition = originalTransition;
  }, 4000);
}

function buildSyntheticFields(data) {
  const enriched = { ...data };

  if (!enriched.item_name) {
    if (enriched.vendor_name && enriched.invoice_number) {
      enriched.item_name = `${enriched.vendor_name} (Inv #${enriched.invoice_number})`;
    } else if (enriched.vendor_name) {
      enriched.item_name = `${enriched.vendor_name} Expense`;
    } else if (enriched.invoice_number) {
      enriched.item_name = `Expense Voucher #${enriched.invoice_number}`;
    }
  }

  if (!enriched.description) {
    const parts = [];
    if (enriched.invoice_number) parts.push(`Voucher/Invoice No: ${enriched.invoice_number}`);
    if (enriched.vendor_name) parts.push(`Purchase From: ${enriched.vendor_name}`);
    if (enriched.gstin) parts.push(`GSTIN: ${enriched.gstin}`);
    if (enriched.subtotal) parts.push(`Taxable: ₹${enriched.subtotal}`);
    if (enriched.cgst) parts.push(`CGST: ₹${enriched.cgst}`);
    if (enriched.sgst) parts.push(`SGST: ₹${enriched.sgst}`);
    if (enriched.total) parts.push(`Total Amount: ₹${enriched.total}`);
    if (parts.length > 0) {
      enriched.description = parts.join(" | ");
    }
  }

  return enriched;
}

function fillERPForm(invoiceData) {
  const filledFields = [];
  const missedFields = [];

  const dataToFill = buildSyntheticFields(invoiceData);
  console.log("[Invoice Assistant] Autofilling ERP with payload:", dataToFill);

  for (const [fieldKey, value] of Object.entries(dataToFill)) {
    if (value === null || value === undefined || value === "") continue;

    const targetInput = findUniversalInput(fieldKey);

    if (targetInput) {
      setNativeValue(targetInput, value);
      highlightElement(targetInput);
      filledFields.push(fieldKey);
      console.log(`[Invoice Assistant] Successfully filled '${fieldKey}':`, value);
    } else {
      missedFields.push(fieldKey);
    }
  }

  // Auto-select currency to INR if present
  const currencySelect = document.querySelector("#currency, select[name='currency']");
  if (currencySelect) {
    setNativeValue(currencySelect, "INR");
    highlightElement(currencySelect);
  }

  return { filledFields, missedFields };
}

// Global invocation helper & message listener
window.__INVOICE_ASSISTANT_FILL__ = fillERPForm;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "FILL_ERP_FORM") {
    const result = fillERPForm(request.data);
    sendResponse({ success: true, ...result });
  }
  return true;
});
