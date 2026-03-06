/**
 * Form persistence utility using sessionStorage (SESSION N Part 6.3).
 * Data persists across tab switches but is cleared on tab close / logout.
 * Expires after 4 hours.
 */

const STORAGE_PREFIX = 'servex_form_';
const EXPIRY_MS = 4 * 60 * 60 * 1000; // 4 hours

/**
 * Save form state to sessionStorage.
 * @param {string} formKey - Unique key for the form (e.g. "invoice_abc123")
 * @param {*} formData - Form data to persist
 */
export function saveFormState(formKey, formData) {
  try {
    const payload = {
      data: formData,
      timestamp: Date.now(),
    };
    sessionStorage.setItem(STORAGE_PREFIX + formKey, JSON.stringify(payload));
  } catch (err) {
    // SessionStorage might be full or unavailable
    console.warn('formPersistence: could not save state', err);
  }
}

/**
 * Load form state from sessionStorage.
 * Returns null if not found or expired.
 * @param {string} formKey
 * @returns {*} form data or null
 */
export function loadFormState(formKey) {
  try {
    const raw = sessionStorage.getItem(STORAGE_PREFIX + formKey);
    if (!raw) return null;

    const payload = JSON.parse(raw);
    if (!payload?.timestamp || !payload?.data) return null;

    // Check expiry
    if (Date.now() - payload.timestamp > EXPIRY_MS) {
      sessionStorage.removeItem(STORAGE_PREFIX + formKey);
      return null;
    }

    return payload.data;
  } catch (err) {
    console.warn('formPersistence: could not load state', err);
    return null;
  }
}

/**
 * Clear a specific form's state.
 * @param {string} formKey
 */
export function clearFormState(formKey) {
  try {
    sessionStorage.removeItem(STORAGE_PREFIX + formKey);
  } catch (err) {
    // ignore
  }
}

/**
 * Clear ALL persisted form states (called on logout).
 */
export function clearAllForms() {
  try {
    const keys = Object.keys(sessionStorage).filter(k => k.startsWith(STORAGE_PREFIX));
    keys.forEach(k => sessionStorage.removeItem(k));
  } catch (err) {
    // ignore
  }
}
