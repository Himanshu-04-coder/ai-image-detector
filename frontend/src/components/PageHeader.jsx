/**
 * Small section header used at the top of each page.
 */
export default function PageHeader({ title, subtitle, icon: Icon, actions }) {
  return (
    <div className="flex items-end justify-between gap-4 mb-6">
      <div className="flex items-center gap-3 min-w-0">
        {Icon && (
          <div className="w-10 h-10 wobbly-2 grid place-items-center
                          bg-paper text-ink
                          border-2 border-pencil">
            <Icon className="w-5 h-5" />
          </div>
        )}
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight truncate font-heading">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-pencil/60">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
    </div>
  );
}
