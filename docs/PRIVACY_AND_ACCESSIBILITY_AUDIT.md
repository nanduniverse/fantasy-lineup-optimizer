# Privacy, accessibility and rights review — September 17, 2026

This is a technical review and a record of unresolved legal questions, not a legal
opinion or a guarantee against claims. The operator confirmed this is a free,
personally operated community project. Location and intended international audience
were not confirmed. Michigan is only a working assumption from the environment,
not a fact asserted in the published policies.

## Implemented

- Separate `/privacy`, `/terms` and `/cookies` pages; contact: nand4ara@gmail.com.
- No separate refund page: there is no payment, subscription, donation or checkout
  implementation. Terms explain that no payments are taken and distinguish third-party charges.
- No analytics, ad pixels, session replay, social widgets or video embeds found in
  app code. Google Fonts and ESPN image requests removed. System fonts and decorative
  initials replace them. No extra alt text on decorative images: adjacent player
  names already convey identity, and original decorative SVGs are hidden from assistive technology.
- Offline saving requires an explicit, unchecked-by-default choice. No app-data
  local storage or service-worker registration before that choice. A storage-choice
  record is used only to honor the choice, not identify visitors. Existing automatic
  caches are removed on the first updated visit without a recorded choice.
- Withdrawal removes app local storage, app Cache Storage and the app service worker,
  then reloads to clear the active league connection. Does not claim to delete
  provider logs, email or ESPN-held information. Expiry is enforced on access;
  remote deletion from an inactive device is not possible.
- League form explains the request and authorization immediately before submission.
  Clicking “Find my league” requests the import; it is not bundled marketing consent.
  No marketing opt-in, newsletter form or unnecessary acceptance checkbox added.
  Existing request-scoped secret handling retained; league API responses now use
  `Cache-Control: no-store`. Credentials are not sent to Blob storage.
- Added skip navigation, explicit focus styling, form error association/focus,
  contrast adjustments, larger controls, mobile reflow, reduced-motion handling,
  readable links and non-color status labels.
- Added CSP, no-referrer, nosniff, anti-framing and camera/microphone/location
  restrictions in the Vercel routing configuration.
- No reviews, testimonials, customer-count claims or certifications found.
  Results now say “modeled win chance” and “highest modeled win probability”.
  No guarantees of winnings, universal accessibility or legal compliance added.
- nflverse data is attributed and linked with its CC BY 4.0 license; transformations
  into projections are disclosed. Third-party rights and non-affiliation are explicit.

## Cookie-consent decision

The source app has no tracking cookies. Optional offline storage is nevertheless
subject to storage/access rules in some jurisdictions, so it now requires an
explicit choice rather than being mislabeled strictly necessary. The small inline
control provides that choice and withdrawal; a separate interrupting cookie banner
would duplicate it. Do not add tracking later without re-evaluating this decision.
The hosting platform can still use operational/security technologies outside the
app's own code; audit them again when enabling any Vercel integration.

[ICO storage/access guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/what-are-storage-and-access-technologies/)
explains that rules extend beyond traditional cookies. Its
[cookie guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/)
distinguishes genuinely necessary storage from merely useful storage.

## Matters that remain unresolved

1. **ESPN permission — substantive priority.** ESPN links its terms to Disney;
   those terms restrict automated extraction and scraping. The project still uses
   undocumented ESPN injury, depth-chart, fantasy-projection and league endpoints.
   A working URL, user import authorization, source credit, or nonprofit intention
   does not establish permission from the provider. Obtain permission or a licensed
   replacement, or disable the integrations if permission cannot be established.
   The public policies do not cure this. No provider license has been verified.
   Sources: [ESPN terms link](https://support.espn.com/hc/en-us/articles/360035445091-Terms-of-Use),
   [Disney terms](https://disneytermsofuse.com/english/).
2. **Content rights.** The [nflverse data license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md)
   is CC BY 4.0; it does not automatically license ESPN material, trademarks or photos.
   [RotoWire's RSS page](https://www.rotowire.com/rss/) describes feeds for blogs and
   personal websites. Retain attribution, links and the current headline-only scope;
   revisit terms before commercialization, expanded syndication or copying articles.
   ESPN RSS and underlying endpoint rights still need confirmation.
3. **Private ESPN credentials.** Copying account-access session cookies is an
   inherently sensitive integration. The app avoids persistence and adds no-store,
   but policy text is not a security audit. Prefer an approved delegated-login flow
   if ESPN offers one; avoid expanding this feature until permission and security
   are reviewed. Never enable request-body logging or place credentials in URLs.
4. **Jurisdiction and operator information.** Being free does not by itself make
   a public website a private/household activity. Confirm operator location and
   audience. A qualified reviewer should determine whether fuller controller
   identification, legal bases, international-transfer terms or local notices
   are required. The site uses an operator email rather than inventing a legal name,
   street address or governing-law clause.
5. **Operations.** Confirm actual Vercel security/runtime-log retention, account
   access controls and mailbox retention. No exact retention promise is invented
   for providers whose settings were not verified. Respond to access/deletion and
   accessibility requests; document a breach-response procedure. The automated
   checks below are not a penetration test or a full manual screen-reader audit.
   Public optimization endpoints can consume server resources; existing computation
   bounds are not an account-wide rate limit. Review Vercel usage limits and abuse
   controls before promoting the site to a larger audience.

## Legal applicability checked, with limits

- US: [FTC privacy/security guidance](https://www.ftc.gov/business-guidance/privacy-security)
  supports collecting only needed information and honoring privacy promises. Whether
  particular FTC/consumer-protection provisions reach this personal project depends
  on its actual activities; “free” is not a substitute for review.
- If operating in Michigan: review the [Michigan Consumer Protection Act](https://www.legislature.mi.gov/documents/mcl/pdf/mcl-act-331-of-1976.pdf)
  for commercial practices, and the Identity Theft Protection Act, MCL 445.72,
  for covered breaches ([official chapter 445](https://www.legislature.mi.gov/documents/mcl/pdf/mcl-chap445.pdf)).
  Applicability depends on covered activities and data. No assertion is made that
  a pending privacy bill is enacted or that Michigan is the only relevant state.
- [California DOJ CCPA guidance](https://www.oag.ca.gov/privacy/ccpa) describes
  business-scope and threshold tests. This personal, free project is not assumed
  covered merely because it is online; growth, monetization or other activities
  could change the analysis. Do not add a misleading “sale opt-out” workflow when
  the app has no sale/sharing mechanism.
- [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng), especially Articles 2–3,
  6, 12–14 and Chapter V: assess territorial scope, the narrow household exception,
  lawful bases and transfers if relevant. Public availability alone does not prove
  every overseas law applies, and a free offering does not automatically exempt it.
- [DOJ web accessibility guidance](https://www.ada.gov/resources/web-guidance/)
  identifies barriers and WCAG as useful technical guidance. ADA coverage of this
  particular personal project is not determined here. We improve access regardless
  and do not claim WCAG certification from automated scans.
- [FTC COPPA FAQ](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions):
  review again if directed to under-13s or collecting their data with actual knowledge.
  No date-of-birth or identity collection is added just to display an age notice.

## Validation

Automated browser coverage includes default absence of app storage/tracking requests,
opt-in and withdrawal, offline reload, direct policy navigation, keyboard skip link,
form-error focus and WCAG-tagged axe checks at desktop and 375/320px widths. Coverage
uses deterministic player fixtures; repeat representative checks against live data.
Full screen-reader, device and legal reviews remain distinct tasks.

Final checks: 120 backend tests passed. The targeted browser checks passed,
including opt-in offline reload and withdrawal. On the deployed production site,
a fresh anonymous Chrome session with real player data had no detected WCAG-tagged
axe violations or horizontal overflow at 1280px and 320px. No external-origin
browser requests, cookies, app local-storage entries or JavaScript errors were
observed in that session before opt-in. The three policy URLs returned HTTP 200;
CSP/referrer headers and no-store league responses were verified. These observations
do not certify every user state, region, assistive technology or future integration.
