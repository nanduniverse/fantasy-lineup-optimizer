export function FootballIcon() {
  return <svg viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M8 32C4 19 19 4 32 8c4 13-11 28-24 24Z" stroke="currentColor" strokeWidth="2" /><path d="m14 26 12-12m-11 7 4 4m0-8 4 4m0-8 4 4M7 25l8 8M25 7l8 8" stroke="currentColor" strokeWidth="2" /></svg>;
}

export function FootballField() {
  return <div className="field-illustration" aria-hidden="true"><svg viewBox="0 0 440 190" fill="none">
    <defs><marker id="route-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="m1 1 6 3-6 3" stroke="#2d6848" strokeWidth="1.5" /></marker></defs>
    <rect x="1" y="1" width="438" height="188" rx="5" fill="#edf4ea" stroke="#d1dfcd" />
    {[30, 106, 182, 258, 334, 410].map((x, i) => <g key={x}><path d={`M${x} 12v166`} stroke="#c5d6bd" /><text x={x + 8} y="27" fill="#a5b89b" fontSize="13" fontFamily="monospace">{i < 3 ? (i + 2) * 10 : (7 - i) * 10}</text></g>)}
    {Array.from({ length: 25 }, (_, i) => <path key={i} d={`M${28 + i * 16} 65v5m0 55v5`} stroke="#bdceb5" />)}
    <path d="M143 13v163" stroke="#639a66" strokeDasharray="4 5" />
    <path d="M126 46h75l34-20h47M126 147h57l33 24h54M130 94h42l27-24h39" stroke="#2d6848" strokeWidth="2" markerEnd="url(#route-arrow)" />
    {[46, 83, 94, 105, 147].map(y => <circle key={y} cx="126" cy={y} r="5" fill="#fdfefa" stroke="#2d6848" strokeWidth="2" />)}
    <circle cx="100" cy="94" r="5" fill="#2d6848" /><circle cx="78" cy="106" r="5" fill="#fdfefa" stroke="#2d6848" strokeWidth="2" />
    {[[157, 42], [156, 80], [156, 105], [159, 150], [202, 100], [243, 115], [300, 48]].map(([x, y]) => <path key={`${x}-${y}`} d={`m${x - 4} ${y - 4} 8 8m-8 0 8-8`} stroke="#9aaa91" strokeWidth="2" />)}
    <text x="311" y="172" fill="#728a62" fontSize="9" fontFamily="monospace" letterSpacing="2">QB / RB / WR / TE</text>
  </svg></div>;
}
