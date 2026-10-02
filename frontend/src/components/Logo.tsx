/**
 * SunuDoctor identity mark.
 *
 * Concept: medical cross (care) + connected nodes (digital network) + a subtle
 * human/community arc — all inside a rounded "shield" that reads as trust.
 * One glyph, three readings, legible down to 16px (favicon).
 */
export function LogoMark({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="SunuDoctor"
      className={className}
      focusable="false"
    >
      <defs>
        <linearGradient id="sd-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0B63CE" />
          <stop offset="55%" stopColor="#0A7BE0" />
          <stop offset="100%" stopColor="#12B8E8" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="17" fill="url(#sd-mark)" />
      {/* Care cross, softly rounded */}
      <path
        d="M27.5 13.5h9a2 2 0 0 1 2 2v9h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-9v9a2 2 0 0 1-2 2h-9a2 2 0 0 1-2-2v-9h-9a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2h9v-9a2 2 0 0 1 2-2z"
        fill="#FFFFFF"
        opacity="0.96"
      />
      {/* Connected-care nodes + human arc */}
      <path
        d="M17 50c3.6-4.2 8.6-6.4 15-6.4S43.4 45.8 47 50"
        stroke="#EAF4FF"
        strokeWidth="2.6"
        strokeLinecap="round"
        fill="none"
        opacity="0.95"
      />
      <circle cx="19" cy="42.5" r="3.1" fill="#EAF4FF" />
      <circle cx="45" cy="42.5" r="3.1" fill="#EAF4FF" />
    </svg>
  );
}

export function Logo({ size = 36, withText = true }: { size?: number; withText?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark size={size} />
      {withText && (
        <span className="text-lg font-bold tracking-tight">
          <span className="text-primary-800">Sunu</span>
          <span className="text-primary">Doctor</span>
        </span>
      )}
    </span>
  );
}
