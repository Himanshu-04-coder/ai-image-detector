import { useRef, useState } from 'react';
import { Upload, ImagePlus } from 'lucide-react';
import { cn } from '../lib/utils';
import { validateImageFile } from '../lib/validation';
import notify from '../lib/toast';

/**
 * Reusable drop zone.
 *  - `multiple`: accepts multiple files (batch)
 *  - `onFiles`:  callback with File[]
 *  - `accept`:   e.g. "image/*"
 *  - `label`:    helper text inside the dashed area
 *  - `validate`: if true (default) we run client-side size/type checks and
 *                toast a friendly error for any rejected file. The check is
 *                a UX nicety - the backend re-validates too.
 */
export default function DropZone({
  multiple = false,
  onFiles,
  accept = 'image/*',
  label = 'Drag & drop an image here, or click to browse',
  validate = true,
}) {
  const inputRef = useRef(null);
  const [over, setOver] = useState(false);

  function pick() {
    inputRef.current?.click();
  }

  function handleFiles(fileList) {
    if (!fileList || !fileList.length) return;
    let files = Array.from(fileList);

    if (validate) {
      const accepted = [];
      files.forEach((f) => {
        const reason = validateImageFile(f);
        if (reason) {
          notify.error(`${f.name}: ${reason}`);
        } else {
          accepted.push(f);
        }
      });
      files = accepted;
      if (files.length === 0) return;
    }

    onFiles(multiple ? files : [files[0]]);
  }

  function onDrop(e) {
    e.preventDefault();
    setOver(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={pick}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && pick()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={cn(
        'group cursor-pointer wobbly-1 border-4 border-pencil p-10',
        'flex flex-col items-center justify-center text-center',
        'transition-colors focus:outline-none focus:ring-2 focus:ring-ink/20',
        over
          ? 'border-ink bg-paper'
          : 'border-pencil bg-paper hover:border-marker'
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="w-14 h-14 wobbly-4 grid place-items-center mb-4
                      bg-white border-2 border-pencil
                      text-ink
                      group-hover:scale-105 transition-transform">
        {multiple ? <ImagePlus className="w-7 h-7" /> : <Upload className="w-7 h-7" />}
      </div>
      <div className="text-sm font-medium">{label}</div>
      <div className="mt-1 text-xs text-pencil/60">
        {multiple ? 'You can select multiple files · max 10MB each' : 'PNG, JPG, or WebP · max 10MB'}
      </div>
    </div>
  );
}
