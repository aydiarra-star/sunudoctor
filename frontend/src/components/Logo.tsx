export function Logo({ size = 36, withText = true }: { size?: number; withText?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5" aria-label="SunuDoctor">
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        role="img"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="logo-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#0B63CE" />
            <stop offset="100%" stopColor="#12B8E8" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#logo-grad)" />
        <path d="M27 14h10v9h9v10h-9v9H27v-9h-9V23h9z" fill="#FFFFFF" opacity="0.95" />
        <circle cx="45" cy="45" r="3.4" fill="#EAF4FF" />
        <circle cx="19" cy="45" r="3.4" fill="#EAF4FF" />
        <path d="M19 45h26" stroke="#EAF4FF" strokeWidth="2.2" strokeLinecap="round" opacity="0.85" />
      </svg>
      {withText && (
        <span className="text-lg font-bold tracking-tight">
          <span className="text-primary-dark">Sunu</span>
          <span className="text-primary">Doctor</span>
        </span>
      )}
    </span>
  );
}
