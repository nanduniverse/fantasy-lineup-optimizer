export const CONTACT = 'nand4ara@gmail.com';
export function SiteFooter() {
  return <footer className="site-footer">
    <p>Free community project. Not affiliated with or endorsed by the NFL, its teams, ESPN or RotoWire.</p>
    <nav aria-label="Policies and contact">
      <a href="/privacy">Privacy policy</a><a href="/terms">Terms and conditions</a><a href="/cookies">Cookie & storage policy</a><a href={`mailto:${CONTACT}`}>Contact: {CONTACT}</a>
    </nav>
    <p>Data: <a href="https://github.com/nflverse/nflverse-data" rel="noreferrer">nflverse contributors</a> · <a href="https://creativecommons.org/licenses/by/4.0/" rel="noreferrer">CC BY 4.0</a>. Data is filtered and transformed into projections. ESPN reports & forecasts; headlines linked to their publishers. <a href="/terms#credits">Credits and rights</a>.</p>
    <p>© {new Date().getFullYear()} Fantasy Lineup Optimizer contributors, for original contributions only. Third-party rights and licenses remain with their owners.</p>
  </footer>;
}
