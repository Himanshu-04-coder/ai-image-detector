import toast from 'react-hot-toast';
import { normalizeError } from '../api/client';

/**
 * Thin wrapper around react-hot-toast that:
 *   - exposes semantic helpers (success / info / warning / error / loading)
 *   - normalises thrown errors via api/client.js so we always show the
 *     same friendly message format
 *
 * Pages should import this rather than `toast` directly so error
 * formatting stays consistent.
 */

export const notify = {
  success(msg, opts) {
    return toast.success(msg, opts);
  },
  error(msg, opts) {
    return toast.error(msg, opts);
  },
  info(msg, opts) {
    return toast(msg, { icon: 'ℹ️', ...opts });
  },
  warning(msg, opts) {
    return toast(msg, { icon: '⚠️', ...opts });
  },
  loading(msg, opts) {
    return toast.loading(msg, opts);
  },
  dismiss(id) {
    return toast.dismiss(id);
  },
  /** Normalise an axios / JS error into a friendly toast. */
  fromError(err, fallback = 'Something went wrong.') {
    const norm = normalizeError(err);
    toast.error(norm.friendlyMessage || fallback);
    return norm;
  },
};

export default notify;
