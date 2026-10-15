// Extension background service worker (Manifest V3)

chrome.runtime.onInstalled.addListener(() => {
  console.log("Invoice to ERP Assistant extension installed successfully.");
});
