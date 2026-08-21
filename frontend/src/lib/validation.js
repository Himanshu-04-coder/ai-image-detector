import { MAX_UPLOAD_BYTES } from '../api/client';

// Same allowed types as backend ALLOWED_CONTENT_TYPES, kept loose because
// browsers report image/jpg, image/jpeg, image/png, image/webp, image/bmp, image/tiff.
const ALLOWED_TYPES = new Set([
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
  'image/bmp',
  'image/tiff',
]);

// Some platforms send empty / generic content-types. We do a light
// extension check as a fallback so we can reject obvious non-images.
const ALLOWED_EXTENSIONS = new Set([
  '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff',
]);

/**
 * Returns a human-friendly error string if the file is invalid, otherwise null.
 * Kept as a pure function so the DropZone and pages can both use it.
 */
export function validateImageFile(file) {
  if (!file) return 'No file selected.';
  if (file.size === 0) return 'The selected file is empty.';
  if (file.size > MAX_UPLOAD_BYTES) {
    const mb = (MAX_UPLOAD_BYTES / 1024 / 1024).toFixed(0);
    const sizeMb = (file.size / 1024 / 1024).toFixed(1);
    return `File is too large (${sizeMb}MB). Maximum allowed size is ${mb}MB.`;
  }
  // Reject if the MIME type AND extension both look wrong.
  const ext = (file.name || '').toLowerCase().slice(file.name.lastIndexOf('.'));
  const looksLikeImage =
    (file.type && ALLOWED_TYPES.has(file.type)) ||
    ALLOWED_EXTENSIONS.has(ext);
  if (!looksLikeImage) {
    return 'Unsupported file type. Please upload a JPG, PNG, WebP, BMP or TIFF image.';
  }
  return null;
}

export { MAX_UPLOAD_BYTES, ALLOWED_TYPES };
