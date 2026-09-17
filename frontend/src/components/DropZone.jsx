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
  prominent = false,
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
        prominent && 'min-h-[clamp(28rem,calc(100vh-13rem),48rem)] px-6 py-12 sm:px-10 sm:py-16',
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
      <div className={cn(
        'wobbly-4 grid place-items-center mb-4 bg-white border-2 border-pencil text-ink group-hover:scale-105 transition-transform',
        prominent ? 'h-20 w-20 mb-7 sm:h-24 sm:w-24' : 'h-14 w-14'
      )}>
        {multiple
          ? <ImagePlus className={prominent ? 'h-10 w-10 sm:h-12 sm:w-12' : 'h-7 w-7'} />
          : <Upload className={prominent ? 'h-10 w-10 sm:h-12 sm:w-12' : 'h-7 w-7'} />}
      </div>
      <div className={cn('font-medium', prominent ? 'text-lg sm:text-2xl' : 'text-sm')}>
        {label}
      </div>
      <div className={cn('mt-1 text-pencil/60', prominent ? 'text-sm sm:text-base' : 'text-xs')}>
        {multiple ? 'You can select multiple files · max 10MB each' : 'PNG, JPG, or WebP · max 10MB'}
      </div>
    </div>
  );
}
