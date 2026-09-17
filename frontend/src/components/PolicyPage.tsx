import { useEffect } from 'react';
import { SiteFooter, CONTACT } from './SiteFooter';
import { StorageSettings } from './StorageSettings';

const titles: Record<string, string> = { '/privacy': 'Privacy policy', '/terms': 'Terms and conditions', '/cookies': 'Cookie & storage policy' };
const contact = <a href={`mailto:${CONTACT}`}>{CONTACT}</a>;
export function PolicyPage({ path }: { path: string }) {
  const title = titles[path];
  useEffect(() => { document.title = `${title} — Fantasy Lineup Optimizer`; }, [title]);
  return <div className="shell policy-shell">
    <a className="skip-link" href="#policy-content">Skip to content</a>
    <nav className="policy-home" aria-label="Main"><a href="/">← Back to lineup optimizer</a></nav>
    <main id="policy-content" className="policy-content" tabIndex={-1}>
      <h1>{title}</h1><p>Last updated: September 17, 2026</p>
      {path === '/privacy' && <>
        <p>Fantasy Lineup Optimizer is a free, personally operated community project. The site operator is responsible for the information practices described here. Contact the operator at {contact} for privacy questions or requests.</p>
        <h2>What is processed and why</h2>
        <ul>
          <li><strong>Using the site:</strong> Vercel hosts the site and API. Requests expose technical information such as IP address, requested URL, time, browser details and errors to the hosting infrastructure for delivery, reliability and security. The app does not add advertising, analytics, session replay, fingerprinting or social-media trackers.</li>
          <li><strong>Matchups:</strong> selected player IDs, scoring format, week and lineup rules are sent to the API when needed to calculate projections. The application does not keep a database of visitors or their matchups.</li>
          <li><strong>Optional league import:</strong> the league ID, selected team, week and any ESPN session credentials you enter pass through the API to ESPN to read your league. Team names, rosters and matchups return to your browser. Only import a league you are authorized to access. The app does not modify your ESPN league.</li>
          <li><strong>Optional offline saving:</strong> only after you enable it, your browser stores public player/news data, matchup player IDs, week, scoring and lineup rules, plus the app files. League names and ESPN session credentials are excluded. See the <a href="/cookies">cookie & storage policy</a>.</li>
          <li><strong>Email:</strong> if you contact the operator, your email address and message are used to respond and handle your request. Do not email passwords, ESPN session cookies, payment details or unnecessary personal information.</li>
        </ul>
        <h2>Storage and retention</h2>
        <p>ESPN credentials are held in browser memory for the connection and processed in server request memory. The application does not deliberately log request bodies or save these credentials to browser storage, server files or cloud snapshots. Disconnect or reload to clear the browser connection. Revoke an ESPN session through ESPN if you believe it was exposed.</p>
        <p>Saved player data and matchup selections expire after 30 days without being rewritten; expired entries are removed when accessed. Your storage choice lasts up to 180 days. App files remain until offline saving is disabled, site data is cleared, or an update replaces them. Browser storage may remain on a device that does not revisit the site; use your browser’s controls to remove it immediately. Cloud snapshots contain public sports data, not private league imports.</p>
        <p>Hosting logs and email are separate from the app’s browser storage. Their retention depends on provider settings and what is needed to handle security issues, requests or legal obligations. Contact the operator about a specific record; clearing browser storage does not delete hosting logs or email.</p>
        <h2>Providers and sharing</h2>
        <p>Vercel processes hosting requests and stores public snapshots; ESPN receives optional league-import requests; email is handled through Gmail. Providers may process information in the United States or other locations under their own terms. The app fetches nflverse, ESPN and RotoWire sports data on the server. Clicking an external article or provider link takes you to that provider’s site and privacy practices.</p>
        <p>The operator does not sell personal information, share it for targeted advertising, or use it for marketing. Information may be disclosed when legally required or needed to address abuse and protect the service. No payment processing or user accounts are offered.</p>
        <h2>Your choices and requests</h2>
        <p>You can use manual player selection without a league import, leave offline saving off, disconnect a league, and clear saved device data from the <a href="/cookies">storage controls</a>. Email {contact} to request access, correction or deletion of information the operator holds, or to report a privacy issue. Verification will be limited to what is reasonably needed; do not send identity documents unless specifically justified.</p>
        <p>Depending on your location and applicable law, you may also have rights to restriction, portability, objection or a complaint to your privacy regulator. Where consent is the basis for optional storage, you can withdraw it at any time without affecting prior lawful processing. The app uses submitted information to provide requested features and technical information to maintain security and reliability; it does not use consent to justify unrelated tracking.</p>
        <h2>Children and changes</h2>
        <p>This is a general-audience sports tool, not a service directed to children under 13. Do not submit a child’s personal information. If you believe such information was submitted, contact the operator so it can be reviewed and removed as appropriate.</p>
        <p>Changes to these practices will be reflected here with an updated date. New optional tracking or new uses requiring consent will not be enabled merely by changing this page.</p>
      </>}
      {path === '/terms' && <>
        <p>These terms describe use of this free community lineup tool. Questions, errors, accessibility issues or rights concerns can be sent to {contact}. Nothing here removes rights you have under applicable law.</p>
        <h2>What this tool does</h2>
        <p>The app estimates fantasy football projections and compares lineups using statistical assumptions. Outputs, injury statuses and news can be incomplete, delayed or wrong. Displayed probabilities are model estimates, not calibrated guarantees. Check official sources and your league’s scoring before making lineup decisions.</p>
        <p>The site does not accept wagers, run paid contests, award prizes, or promise wins or earnings. It is not betting advice. You remain responsible for your choices and compliance with your league and applicable rules.</p>
        <h2>Permitted use and league access</h2>
        <p>Use the service lawfully. Do not try to access another person’s private league without permission, bypass access controls, upload malicious content, or disrupt the service. Enter only credentials that you are authorized to use, and respect ESPN’s terms. An import authorization does not grant permission from ESPN or override its rules.</p>
        <h2>Price and refunds</h2>
        <p>This site is free. It has no checkout, subscription, paid feature or donation collection, so it takes no payments to refund. Charges by ESPN, a league, or another third party are governed by that party’s policies. Any future paid feature would require separate, clearly disclosed pricing and payment terms before purchase.</p>
        <h2 id="credits">Credits, copyright and third-party rights</h2>
        <p>Roster and historical statistics are provided by <a href="https://github.com/nflverse/nflverse-data" rel="noreferrer">nflverse contributors</a> under <a href="https://creativecommons.org/licenses/by/4.0/" rel="noreferrer">Creative Commons Attribution 4.0</a>. This app filters and combines data and calculates its own projections and workload adjustments. The source data is supplied without warranties under its license; that license’s permissions remain available to you.</p>
        <p>ESPN supplies reports and forecasts. News links identify ESPN or RotoWire as their source. Third-party names, data and content remain subject to their owners’ rights and terms; their inclusion is not a claim of ownership, endorsement or a redistribution license. The site is not affiliated with the NFL, its teams, ESPN or RotoWire.</p>
        <p>For a copyright or other rights concern, email {contact} with the affected URL, a description of the material, your relationship to the rights holder and a way to contact you. Requests will be reviewed; this contact is not a representation that a registered DMCA agent or statutory safe harbor exists.</p>
        <h2>Availability and responsibility</h2>
        <p>The service is provided as available and may change or stop. To the extent permitted by law, the operator does not warrant uninterrupted service or the accuracy or completeness of estimates and third-party data. Nothing in these terms excludes liability that cannot lawfully be excluded, including applicable consumer rights. There is no mandatory arbitration or waiver of statutory rights in these terms.</p>
        <h2>Privacy and accessibility</h2>
        <p>The <a href="/privacy">privacy policy</a> describes data handling. If a feature is inaccessible, email {contact} with the page and the task you were trying to complete. Include browser or assistive-technology details only if you wish; do not include account secrets. Accessibility reports help prioritize fixes; no certification of universal accessibility is claimed.</p>
      </>}
      {path === '/cookies' && <>
        <p>The app does not set advertising or analytics cookies and does not embed third-party videos, social widgets, remote fonts or player images. Optional offline storage is off until you choose it. A separate tracking-consent banner is not used because the app has no optional tracking.</p>
        <h2>Storage used by the app</h2>
        <ul>
          <li><strong>Storage preference:</strong> a local-storage record remembers your on/off choice for up to 180 days. It is used only to honor that choice.</li>
          <li><strong>Offline data, only if enabled:</strong> public catalogs, news and selected matchup settings are saved on this device. Records expire 30 days after their last save and are removed when accessed after expiry. No ESPN session credentials are saved.</li>
          <li><strong>Offline app files, only if enabled:</strong> a service worker caches the app so it can open without a network. These files are replaced on updates or removed when saving is turned off. Clearing site data in your browser also removes them.</li>
        </ul>
        <p>Standard browser networking caches and security measures may also operate. Vercel may use necessary security technologies to deliver and protect the site. This app does not use those for advertising. ESPN session cookies entered in a private-league form are used only for the requested server-side import; the app does not install ESPN cookies in your browser.</p>
        <h2>Change your choice</h2>
        <p>Online use works with offline saving disabled. Enabling saving reloads the page to cache current data. Turning it off removes the app’s saved data and reloads, clearing the active league connection. It does not delete data held by ESPN, your browser’s general HTTP cache, hosting logs or emails.</p>
        <StorageSettings />
        <p>Your choice applies to this browser on this device. External sites you choose to visit have their own cookies and settings. See the <a href="/privacy">privacy policy</a> or contact {contact} for help.</p>
      </>}
    </main><SiteFooter />
  </div>;
}
