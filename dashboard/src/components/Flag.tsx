/** Small inline SVG flags for the language picker (emoji flags do not render on Windows). 3:2, 30×20 units. */
import type {ReactNode} from 'react';

function star(cx: number, cy: number, r: number, rotate = -90): string {
  return Array.from({length: 10}, (_, i) => {
    const radius = i % 2 ? r * 0.4 : r;
    const angle = ((rotate + i * 36) * Math.PI) / 180;
    return `${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`;
  }).join(' ');
}

const stripes = (colors: string[], vertical = false) => colors.map((color, i) => vertical
  ? <rect key={i} x={(30 / colors.length) * i} width={30 / colors.length + 0.1} height={20} fill={color}/>
  : <rect key={i} y={(20 / colors.length) * i} width={30} height={20 / colors.length + 0.1} fill={color}/>);

const FLAGS: Record<string, ReactNode> = {
  en: <>
    <rect width={30} height={20} fill="#012169"/>
    <path d="M0 0L30 20M30 0L0 20" stroke="#fff" strokeWidth={4}/>
    <path d="M0 0L30 20M30 0L0 20" stroke="#C8102E" strokeWidth={1.4}/>
    <path d="M15 0V20M0 10H30" stroke="#fff" strokeWidth={6}/>
    <path d="M15 0V20M0 10H30" stroke="#C8102E" strokeWidth={3.4}/>
  </>,
  zh: <>
    <rect width={30} height={20} fill="#EE1C25"/>
    <polygon points={star(5.5, 5.5, 3.2)} fill="#FFFF00"/>
    {[[10.5, 2.2, -50], [12.5, 4.4, -20], [12.5, 7.4, 10], [10.5, 9.4, 40]].map(([x, y, a]) =>
      <polygon key={`${x}${y}`} points={star(x, y, 1.1, a)} fill="#FFFF00"/>)}
  </>,
  hi: <>
    {stripes(['#FF9933', '#FFFFFF', '#138808'])}
    <circle cx={15} cy={10} r={2.6} fill="none" stroke="#000080" strokeWidth={0.6}/>
    <circle cx={15} cy={10} r={0.6} fill="#000080"/>
  </>,
  es: <>
    <rect width={30} height={20} fill="#AA151B"/>
    <rect y={5} width={30} height={10} fill="#F1BF00"/>
  </>,
  ar: <>
    <rect width={30} height={20} fill="#006C35"/>
    <path d="M8 7.5c2-1.5 3 1 5 0s3-1.5 5 0 3 1 4 0" stroke="#fff" strokeWidth={0.9} fill="none" strokeLinecap="round"/>
    <path d="M9 10c2-1 4 .8 6 0s3-1 6 0" stroke="#fff" strokeWidth={0.9} fill="none" strokeLinecap="round"/>
    <path d="M8 14h14l1.5-.8" stroke="#fff" strokeWidth={0.9} fill="none" strokeLinecap="round"/>
  </>,
  fr: <>{stripes(['#002395', '#FFFFFF', '#ED2939'], true)}</>,
  bn: <>
    <rect width={30} height={20} fill="#006A4E"/>
    <circle cx={13.5} cy={10} r={6} fill="#F42A41"/>
  </>,
  pt: <>
    <rect width={30} height={20} fill="#009C3B"/>
    <polygon points="15,2 28,10 15,18 2,10" fill="#FFDF00"/>
    <circle cx={15} cy={10} r={4.6} fill="#002776"/>
    <path d="M10.6 9.2c3-1.2 6-.8 8.8 1" stroke="#fff" strokeWidth={0.8} fill="none"/>
  </>,
  ru: <>{stripes(['#FFFFFF', '#0039A6', '#D52B1E'])}</>,
  ur: <>
    <rect width={30} height={20} fill="#01411C"/>
    <rect width={7.5} height={20} fill="#fff"/>
    <circle cx={19} cy={10} r={5} fill="#fff"/>
    <circle cx={20.6} cy={8.8} r={4.4} fill="#01411C"/>
    <polygon points={star(22.3, 7.4, 1.6, -60)} fill="#fff"/>
  </>,
  he: <>
    <rect width={30} height={20} fill="#fff"/>
    <rect y={2} width={30} height={2.2} fill="#0038B8"/>
    <rect y={15.8} width={30} height={2.2} fill="#0038B8"/>
    <path d="M15 6.4l3.2 5.5h-6.4zM15 13.6l3.2-5.5h-6.4z" fill="none" stroke="#0038B8" strokeWidth={0.8}/>
  </>,
};

export function Flag({code, size = 20}: {code: string; size?: number}) {
  const flag = FLAGS[code];
  if (!flag) return null;
  // Rounded corners come from CSS (.flag), so no clipPath ids repeat when the same flag is shown twice.
  return <svg className="flag" width={size} height={(size * 2) / 3} viewBox="0 0 30 20" aria-hidden="true">{flag}</svg>;
}
