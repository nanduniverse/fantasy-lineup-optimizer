import { NewsPanel } from "./components/NewsPanel";
import { NflBuilder } from "./components/NflBuilder";
import { FootballField, FootballIcon } from "./components/FootballField";

export default function App() {
  return <main className="shell">
    <nav className="topbar"><a className="brand" href="/" aria-label="Fantasy Football home"><span className="brand-icon"><FootballIcon /></span><span className="brand-label">FANTASY<br />FOOTBALL</span></a><div className="nav-meta"><span>2026 MATCHUPS</span><span className="season-badge"><i /> NFL 2026 / 27</span></div></nav>
    <header className="hero"><div><p className="eyebrow">2026 NFL · REGULAR SEASON</p><h1>Lineup optimizer</h1><p className="lede">Add your roster and your opponent’s starters to compare lineups.</p></div><FootballField /></header>
    <NflBuilder />
    <NewsPanel />
    <footer><strong>NFL · 2026 / 27</strong><span>Stats: nflverse · Weekly reports & forecasts: ESPN</span></footer>
  </main>;
}
