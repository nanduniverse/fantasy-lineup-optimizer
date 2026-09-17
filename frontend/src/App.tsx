import { SiteFooter } from "./components/SiteFooter";
import { StorageSettings } from "./components/StorageSettings";
import { NewsPanel } from "./components/NewsPanel";
import { NflBuilder } from "./components/NflBuilder";
import { FootballField, FootballIcon } from "./components/FootballField";

export default function App() {
  return <div className="shell"><a className="skip-link" href="#main-content">Skip to content</a>
    <nav className="topbar"><a className="brand" href="/" aria-label="Fantasy Football home"><span className="brand-icon"><FootballIcon /></span><span className="brand-label">FANTASY<br />FOOTBALL</span></a><div className="nav-meta"><span>2026 MATCHUPS</span><span className="season-badge"><i /> NFL 2026 / 27</span></div></nav>
    <main id="main-content" tabIndex={-1}><header className="hero"><div><p className="eyebrow">2026 NFL · REGULAR SEASON</p><h1>Lineup optimizer</h1><p className="lede">Add your roster and your opponent’s starters to compare lineups.</p></div><FootballField /></header>
    <StorageSettings />
    <NflBuilder />
    <NewsPanel />
    </main><SiteFooter />
  </div>;
}
