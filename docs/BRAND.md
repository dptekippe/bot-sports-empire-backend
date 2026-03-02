# DynastyDroid Brand Assets

## SVG Logo (Bot Head)

```html
<a href="/" class="logo-container">
    <svg class="logo-droid" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="headGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#0a0a15;stop-opacity:1" />
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        <!-- Droid Head -->
        <path d="M50 15 L80 30 L80 70 L50 85 L20 70 L20 30 Z" 
              fill="url(#headGrad)" stroke="#00e5ff" stroke-width="1.5"/>
        <!-- Eyes - Glowing Cyan -->
        <circle cx="38" cy="45" r="10" fill="#00e5ff" filter="url(#glow)"/>
        <circle cx="62" cy="45" r="10" fill="#00e5ff" filter="url(#glow)"/>
        <!-- Eye Highlights -->
        <circle cx="38" cy="45" r="4" fill="#ffffff"/>
        <circle cx="62" cy="45" r="4" fill="#ffffff"/>
        <!-- Antenna -->
        <line x1="50" y1="15" x2="50" y2="8" stroke="#00e5ff" stroke-width="1.5"/>
        <circle cx="50" cy="6" r="3" fill="#00e5ff" filter="url(#glow)"/>
    </svg>
    <span class="logo-text">
        <span class="logo-dynasty">DYNASTY</span><span class="logo-droid-text">DROID</span>
    </span>
</a>
```

## CSS

```css
.logo-droid {
    height: 36px;
    width: 36px;
}
.logo-text {
    font-family 'Segoe UI', Roboto,: 'Inter', sans-serif;
    font-size: 24px;
    line-height: 1;
}
.logo-dynasty {
    font-weight: 800;
    color: #ffffff;
}
.logo-droid-text {
    font-weight: 200;
    color: #ffffff;
}
```

## Bot Avatar SVG

```html
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="helmetGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#2a2a3e;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#1a1a2e;stop-opacity:1" />
        </linearGradient>
        <filter id="avatarGlow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    <!-- Helmet -->
    <ellipse cx="50" cy="50" rx="35" ry="38" fill="url(#helmetGrad)" stroke="#00e5ff" stroke-width="1.5"/>
    <!-- Visor -->
    <ellipse cx="50" cy="48" rx="25" ry="12" fill="#00e5ff" filter="url(#avatarGlow)"/>
    <ellipse cx="50" cy="48" rx="20" ry="8" fill="#0a0a15"/>
    <!-- Eye lights -->
    <circle cx="42" cy="48" r="3" fill="#00e5ff" filter="url(#avatarGlow)"/>
    <circle cx="58" cy="48" r="3" fill="#00e5ff" filter="url(#avatarGlow)"/>
</svg>
```

## Color Palette
- Primary: #00e5ff (Cyan)
- Glow: rgba(0, 229, 255, 0.6)
- Background Dark: #0a0a0f, #1a1a2e, #0a0a15
