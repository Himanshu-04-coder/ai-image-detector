import axios from 'axios';

// Base URL is read from .env (VITE_API_URL). Defaults to localhost:8000 in dev.
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Centralised max upload size. Keep this in sync with MAX_UPLOAD_BYTES on
// the backend (currently 10MB). Used by the DropZone / pre-upload checks so
// we can show a friendly toast before the request goes out and burns bandwidth.
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

const api = axios.create({
  baseURL,
  timeout: 60000,
});

// --- Error normalisation ---------------------------------------------------
// Every error coming out of the API client has:
//   - `friendlyMessage`: a one-line string safe to show in toasts / UI
//   - `kind`: 'network' | 'timeout' | 'client' | 'server' | 'unknown'
//   - `status`: numeric HTTP status (or null for network errors)
//   - `original`: the underlying axios error
// This lets pages decide how to render errors without re-implementing the
// axios-error -> human-message logic everywhere.

export function normalizeError(err) {
  // No response from server = network/connection problem.
  if (err && err.code === 'ERR_NETWORK') {
    return {
      friendlyMessage:
        'Cannot reach the backend server. Make sure the FastAPI service is ' +
        'running on ' + baseURL + '.',
      kind: 'network',
      status: null,
      original: err,
    };
  }
  if (err && err.code === 'ECONNABORTED') {
    return {
      friendlyMessage:
        'The request took too long and was cancelled. Please try again.',
      kind: 'timeout',
      status: null,
      original: err,
    };
  }
  if (err && err.response) {
    const status = err.response.status;
    const detail =
      err.response.data?.error ||
      err.response.data?.detail ||
      err.response.data?.message ||
      err.message;
    if (status >= 500) {
      return {
        friendlyMessage:
          'Server error (' + status + '). ' + (detail || 'Please try again later.'),
        kind: 'server',
        status,
        original: err,
      };
    }
    if (status === 413) {
      return {
        friendlyMessage:
          'The image is too large. Max allowed size is ' +
          (MAX_UPLOAD_BYTES / 1024 / 1024) + 'MB.',
        kind: 'client',
        status,
        original: err,
      };
    }
    if (status === 415) {
      return {
        friendlyMessage:
          'Unsupported file type. Please upload a JPG, PNG, WebP, BMP or TIFF image.',
        kind: 'client',
        status,
        original: err,
      };
    }
    return {
      friendlyMessage: detail || 'Request failed (' + status + ').',
      kind: 'client',
      status,
      original: err,
    };
  }
  return {
    friendlyMessage:
      (err && err.message) || 'Something went wrong. Please try again.',
    kind: 'unknown',
    status: null,
    original: err,
  };
}

// --- Single image endpoints -------------------------------------------------

/** Quick verdict + confidence for one image. */
export async function predict(file, onUploadProgress) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/predict', form, {
    onUploadProgress,
  });
  return data;
}

/** Full detailed analysis: verdict, confidence, gradcam, exif, frequency. */
export async function predictDetailed(file, onUploadProgress) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/predict-detailed', form, {
    onUploadProgress,
  });
  return data;
}

/** Batch prediction for many images at once. */
export async function predictBatch(files, onUploadProgress) {
  const form = new FormData();
  files.forEach((file) => form.append('files', file));
  const { data } = await api.post('/predict-batch', form, {
    onUploadProgress,
  });
  return data;
}

// --- History + stats --------------------------------------------------------

export async function getHistory() {
  const { data } = await api.get('/history');
  return data;
}

export async function getStats() {
  const { data } = await api.get('/stats');
  return data;
}

// --- Health check -----------------------------------------------------------
// Used by the connection-status indicator on the page. Returns true if the
// backend responds, false otherwise. Swallows errors.
export async function ping() {
  try {
    await api.get('/', { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

export default api;
