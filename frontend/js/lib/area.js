/**
 * Is a remote job open to you? The same rules as backend/app/services/area.py:
 * a remote job is open unless its location limits it to countries you're not
 * in (worked out from the locations on your profile, e.g. "Edmonton, AB").
 */
const PROVINCES = {
  ab: "alberta",
  bc: "british columbia",
  mb: "manitoba",
  nb: "new brunswick",
  nl: "newfoundland",
  ns: "nova scotia",
  nt: "northwest territories",
  nu: "nunavut",
  on: "ontario",
  pe: "prince edward island",
  qc: "quebec",
  sk: "saskatchewan",
  yt: "yukon",
};
const US_STATES =
  "al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc".split(
    " ",
  );
const COUNTRIES = {
  canada: /canada|canadian/,
  "united states":
    /united states|\busa\b|\bu\.s\.|\bus\b|\bamerica\b|bay area|san francisco|new york|\bnyc\b|seattle|boston|chicago|austin|los angeles|denver|atlanta|miami|texas|california|washington,? d\.?c/,
  "united kingdom": /united kingdom|\buk\b|england|scotland|wales/,
  europe: /europe|\bemea\b|\beu\b/,
  ireland: /ireland/,
  germany: /germany/,
  france: /france/,
  spain: /spain/,
  portugal: /portugal/,
  netherlands: /netherlands/,
  poland: /poland/,
  india: /india/,
  asia: /\bapac\b|\basia\b|singapore|japan|philippines/,
  australia: /australia|new zealand/,
  "latin america": /latam|latin america|brazil|mexico|argentina|colombia/,
  israel: /israel/,
};
const OPEN_TO_ALL = /anywhere|worldwide|global|international/;
const code = (c) => new RegExp(`,\\s*${c}\\b`);
const city = (loc) => loc.split(",")[0].trim().toLowerCase();

export function userArea(locations) {
  const cities = new Set();
  const countries = new Set();
  for (const loc of locations) {
    const text = loc.toLowerCase();
    cities.add(city(loc));
    for (const [c, name] of Object.entries(PROVINCES)) {
      if (code(c).test(text) || text.includes(name)) countries.add("canada");
    }
    if (US_STATES.some((c) => !(c in PROVINCES) && code(c).test(text)))
      countries.add("united states");
    for (const [country, re] of Object.entries(COUNTRIES))
      if (re.test(text)) countries.add(country);
    if (text.includes("north america")) {
      countries.add("canada");
      countries.add("united states");
    }
  }
  cities.delete("");
  return { cities, countries };
}

function countriesIn(location) {
  const text = (location ?? "").toLowerCase();
  const found = new Set(
    Object.entries(COUNTRIES)
      .filter(([, re]) => re.test(text))
      .map(([c]) => c),
  );
  if (text.includes("north america")) {
    found.add("canada");
    found.add("united states");
  }
  if (
    Object.entries(PROVINCES).some(
      ([c, name]) => code(c).test(text) || text.includes(name),
    )
  )
    found.add("canada");
  return found;
}

// Words in a location that aren't places: "Remote (Hybrid) - HQ" names no place at all.
const NOT_PLACES =
  /\b(remote|hybrid|flexible|work from home|wfh|home|office|offices|hq|headquarters|based|first|only|within|in|or|and|the|of|any|location|locations|multiple|various|can)\b/g;

/**
 * A remote job is open to you if its location names your country, province or
 * city, or names no place at all ("Remote"). Naming only other places
 * ("Remote, United States", "Remote, Sweden") means it isn't.
 */
export function remoteOpenToYou(location, area) {
  if (!area.countries.size) return true;
  const text = (location ?? "").toLowerCase();
  if (OPEN_TO_ALL.test(text) || [...area.cities].some((c) => text.includes(c)))
    return true;
  const named = countriesIn(location);
  if ([...named].some((c) => area.countries.has(c))) return true;
  if (/\bcan\b/.test(text) && area.countries.has("canada")) return true;
  const leftover = text
    .replace(NOT_PLACES, " ")
    .replace(/[^a-z]+/g, " ")
    .trim();
  return leftover === "";
}
