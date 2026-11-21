interface BotIconProps {
  icon: string;
  color?: string;
  size?: number;
  className?: string;
}

export const BotIcon = ({ icon, color, size = 28, className = '' }: BotIconProps) => {
  const iconId = icon.toLowerCase();
  const accentColor = color || '#3b82f6';
  void accentColor;

  switch (iconId) {
    case 'flame':
      // Flame / teardrop emblem (firstmate-oss)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="flame-grad" x1="4" y1="4" x2="24" y2="24" gradientUnits="userSpaceOnUse">
              <stop stopColor="#fb7185" />
              <stop offset="1" stopColor="#e11d48" />
            </linearGradient>
            <filter id="flame-glow" x="0" y="0" width="28" height="28" filterUnits="userSpaceOnUse">
              <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#f43f5e" floodOpacity="0.4" />
            </filter>
          </defs>
          <path
            d="M14 3C14 3 6 12 6 17.5C6 21.6421 9.58172 25 14 25C18.4183 25 22 21.6421 22 17.5C22 12 14 3 14 3Z"
            fill="url(#flame-grad)"
            filter="url(#flame-glow)"
          />
          <path
            d="M14 10C14 10 10 15 10 18.5C10 20.7091 11.7909 22.5 14 22.5C16.2091 22.5 18 20.7091 18 18.5C18 15 14 10 14 10Z"
            fill="#ffe4e6"
            fillOpacity="0.85"
          />
        </svg>
      );

    case 'wedge':
      // Triangular curved delta wedge (treehouse)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="wedge-grad" x1="5" y1="5" x2="23" y2="23" gradientUnits="userSpaceOnUse">
              <stop stopColor="#60a5fa" />
              <stop offset="1" stopColor="#2563eb" />
            </linearGradient>
          </defs>
          <path
            d="M14 4C15.2 4 16.1 4.7 16.7 5.7L23.2 19C24 20.6 22.8 22.5 21 22.5H7C5.2 22.5 4 20.6 4.8 19L11.3 5.7C11.9 4.7 12.8 4 14 4Z"
            fill="url(#wedge-grad)"
          />
          <circle cx="14" cy="16" r="3" fill="#dbeafe" fillOpacity="0.9" />
        </svg>
      );

    case 'pill':
      // Capsule / lozenge emblem (runner-up)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="pill-grad" x1="4" y1="14" x2="24" y2="14" gradientUnits="userSpaceOnUse">
              <stop stopColor="#fbbf24" />
              <stop offset="1" stopColor="#d97706" />
            </linearGradient>
          </defs>
          <rect x="5" y="8" width="18" height="12" rx="6" fill="url(#pill-grad)" />
          <path d="M14 8V20" stroke="#78350f" strokeWidth="1.5" strokeOpacity="0.4" />
          <circle cx="9.5" cy="14" r="1.5" fill="#fef3c7" />
          <circle cx="18.5" cy="14" r="1.5" fill="#fef3c7" />
        </svg>
      );

    case 'droplet':
      // Cyan tear / organic droplet (no-mistakes)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="drop-grad" x1="5" y1="5" x2="23" y2="23" gradientUnits="userSpaceOnUse">
              <stop stopColor="#22d3ee" />
              <stop offset="1" stopColor="#0891b2" />
            </linearGradient>
          </defs>
          <path
            d="M6 14C6 8.5 11 4 16 4C19.5 4 23 7.5 23 12C23 18 17.5 24 11 24C7.5 24 6 21 6 14Z"
            fill="url(#drop-grad)"
          />
          <path
            d="M10 13C10 9 13 6 16.5 6"
            stroke="#cffafe"
            strokeWidth="2"
            strokeLinecap="round"
            strokeOpacity="0.8"
          />
        </svg>
      );

    case 'shield':
      // Polygon / shield emblem (gnhf)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="shield-grad" x1="5" y1="4" x2="23" y2="24" gradientUnits="userSpaceOnUse">
              <stop stopColor="#f472b6" />
              <stop offset="1" stopColor="#db2777" />
            </linearGradient>
          </defs>
          <path
            d="M14 4L22 7.5V14.5C22 19.5 18 23 14 24.5C10 23 6 19.5 6 14.5V7.5L14 4Z"
            fill="url(#shield-grad)"
          />
          <path
            d="M11 14L13 16.5L17 11.5"
            stroke="#fdf2f8"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case 'star':
      // Hexagon / facet star emblem (gh-axi)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="star-grad" x1="5" y1="5" x2="23" y2="23" gradientUnits="userSpaceOnUse">
              <stop stopColor="#a78bfa" />
              <stop offset="1" stopColor="#7c3aed" />
            </linearGradient>
          </defs>
          <path
            d="M14 4L21.8 8.5V17.5L14 22L6.2 17.5V8.5L14 4Z"
            fill="url(#star-grad)"
          />
          <circle cx="14" cy="13" r="3.2" fill="#ede9fe" />
        </svg>
      );

    case 'target':
    default:
      // Crimson circle / radar target emblem (backpass)
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform duration-150 ${className}`}
        >
          <defs>
            <linearGradient id="target-grad" x1="4" y1="4" x2="24" y2="24" gradientUnits="userSpaceOnUse">
              <stop stopColor="#f87171" />
              <stop offset="1" stopColor="#dc2626" />
            </linearGradient>
          </defs>
          <circle cx="14" cy="14" r="10" fill="url(#target-grad)" />
          <circle cx="14" cy="14" r="6" stroke="#fee2e2" strokeWidth="1.5" fill="none" />
          <circle cx="14" cy="14" r="2.5" fill="#fee2e2" />
        </svg>
      );
  }
};
