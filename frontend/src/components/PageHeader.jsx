// Consistent page header: eyebrow for section context, a balanced
// title, optional description, and actions pinned to the right. Every
// top-level page opens with this so the app reads as one product.
export default function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 pb-6 mb-8 border-b border-zinc-200 dark:border-zinc-800">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-widest text-accent-600 dark:text-accent-400 mb-1.5">
            {eyebrow}
          </p>
        )}
        <h1
          className="text-2xl lg:text-[28px] font-bold tracking-tight text-zinc-900 dark:text-white"
          style={{ textWrap: 'balance' }}
        >
          {title}
        </h1>
        {description && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1.5 max-w-2xl">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
