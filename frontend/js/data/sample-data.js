/**
 * SAMPLE DATA: used only when config.apiMode is "mock" (the default).
 *
 * Every company, person and job posting here is FICTIONAL, and every link
 * points to example.com. Dates are generated relative to today, so the demo
 * never looks out of date. Nothing here is a real listing or application.
 *
 * scoreJob() near the middle is the explainable match score: each factor
 * scores 0-1, is multiplied by a fixed weight, and carries the evidence shown
 * on the job page. It's a good first version of the backend's matching logic.
 */
import { addDays, toDateOnly } from "../lib/format.js";
import { remoteOpenToYou, userArea } from "../lib/area.js";

// ---------------------------------------------------------------- time helpers
function daysAgoIso(now, days, hour = 9, minute = 0) {
  const d = new Date(now);
  d.setDate(d.getDate() - days);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString();
}

function daysAgoDate(now, days) {
  const d = new Date(now);
  d.setDate(d.getDate() - days);
  return toDateOnly(d);
}

// ---------------------------------------------------------------- companies
const COMPANIES = [
  {
    id: "co_northline",
    name: "Northline Energy Analytics",
    website: "https://northline.example.com",
  },
  {
    id: "co_prairiehealth",
    name: "Prairie Health Data Co-op",
    website: "https://prairiehealth.example.com",
  },
  {
    id: "co_bowridge",
    name: "Bowridge Software",
    website: "https://bowridge.example.com",
  },
  {
    id: "co_kestrel",
    name: "Kestrel Insurance Group",
    website: "https://kestrel.example.com",
  },
  {
    id: "co_ravine",
    name: "Ravine Logistics",
    website: "https://ravine.example.com",
  },
  {
    id: "co_aspen",
    name: "Aspen Grove Credit Union",
    website: "https://aspengrove.example.com",
  },
  {
    id: "co_tamarack",
    name: "Tamarack Civil",
    website: "https://tamarack.example.com",
  },
  {
    id: "co_lumen",
    name: "Lumen Retail Systems",
    website: "https://lumenretail.example.com",
  },
  { id: "co_cityops", name: "River Valley Municipal Services", website: null },
  {
    id: "co_fieldnote",
    name: "Fieldnote Labs",
    website: "https://fieldnote.example.com",
  },
];

// ---------------------------------------------------------------- profile
export function createProfile(now) {
  return {
    id: "cand_001",
    full_name: "Jordan Lee",
    email: "jordan.lee@example.com",
    headline: "IT coordinator moving into data engineering",
    summary:
      "Four years of IT support and systems administration, now building data pipelines in Python and SQL. Automates onboarding workflows, maintains reporting in Power BI, and is finishing a BSc in computing.",
    preferred_titles: [
      "Data Engineer",
      "Analytics Engineer",
      "BI Developer",
      "Data Analyst",
    ],
    locations: ["Edmonton, AB", "Calgary, AB"],
    work_arrangements: ["hybrid", "remote", "onsite"],
    salary_min: 75_000,
    salary_max: 105_000,
    salary_currency: "CAD",
    exclusions: ["Senior", "Principal", "Sales"],
    skills: [
      { name: "Python", proficiency: "proficient", years: 3 },
      { name: "SQL", proficiency: "proficient", years: 4 },
      { name: "PostgreSQL", proficiency: "proficient", years: 2 },
      { name: "Power BI", proficiency: "expert", years: 3 },
      { name: "Power Automate", proficiency: "expert", years: 3 },
      { name: "Git", proficiency: "proficient", years: 3 },
      { name: "Docker", proficiency: "familiar", years: 1 },
      { name: "Azure", proficiency: "familiar", years: 1 },
      { name: "REST APIs", proficiency: "proficient", years: 2 },
      { name: "Excel", proficiency: "expert", years: 6 },
    ],
    experience: [
      {
        id: "exp_1",
        title: "IT Business Coordinator",
        company: "Riverbend Health Services",
        start_month: "2025-02",
        end_month: null,
        description:
          "Built Power Automate flows for staff onboarding and offboarding. Maintains Power BI reporting and SharePoint ticket tracking for a contact centre.",
      },
      {
        id: "exp_2",
        title: "Systems Administrator (co-op)",
        company: "Tamarack Construction",
        start_month: "2024-09",
        end_month: "2025-01",
        description:
          "Desktop support for site and remote staff; decommissioned servers at closing project sites.",
      },
    ],
    education: [
      {
        id: "edu_1",
        institution: "Northern Plains University",
        credential: "BSc",
        field: "Computing and Information Systems",
        end_month: "2026-12",
        in_progress: true,
      },
      {
        id: "edu_2",
        institution: "Lakeshore Polytechnic",
        credential: "Diploma",
        field: "Computer Networking and Technical Support",
        end_month: "2020-04",
        in_progress: false,
      },
    ],
    updated_at: daysAgoIso(now, 3, 20),
  };
}

const JOB_SEEDS = [
  {
    source: "greenhouse",
    company: 0,
    title: "Data Engineer",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [85_000, 105_000],
    foundDaysAgo: 0,
    review: "new",
    required: ["Python", "SQL", "PostgreSQL"],
    preferred: ["Airflow", "Docker"],
    intro:
      "Northline turns pipeline and well-site telemetry into daily operating reports for field teams across Alberta.",
    duties: [
      "Build and maintain batch ingestion jobs that land sensor data in PostgreSQL",
      "Model clean, tested tables for the reporting team",
      "Monitor pipeline runs and fix failures before the morning reports",
    ],
  },
  {
    source: "lever",
    company: 3,
    title: "Analytics Engineer",
    location: "Calgary, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [90_000, 110_000],
    foundDaysAgo: 0,
    review: "new",
    required: ["SQL", "dbt", "Python"],
    preferred: ["Snowflake", "Power BI"],
    intro:
      "Kestrel's analytics team supports pricing and claims with a modern warehouse and a small, senior-friendly team.",
    duties: [
      "Own dbt models for claims and policy data",
      "Write data tests and documentation",
      "Partner with actuaries on new metrics",
    ],
  },
  {
    source: "greenhouse",
    company: 2,
    title: "Junior Data Engineer",
    location: null,
    arrangement: "remote",
    type: "full_time",
    salary: [70_000, 85_000],
    foundDaysAgo: 1,
    review: "new",
    required: ["Python", "SQL"],
    preferred: ["Docker", "Git", "AWS"],
    intro:
      "Bowridge builds scheduling software for clinics. You will join a three-person data team, remote within Canada.",
    duties: [
      "Write and test Python extract jobs for customer data",
      "Maintain the event warehouse schema",
      "Pair with senior engineers on pipeline reviews",
    ],
  },
  {
    source: "adzuna",
    company: 1,
    title: "BI Developer",
    location: "Edmonton, AB",
    arrangement: "onsite",
    type: "contract",
    salary: [80_000, 95_000],
    foundDaysAgo: 1,
    review: "shortlisted",
    required: ["Power BI", "SQL"],
    preferred: ["Azure", "DAX"],
    intro:
      "A 12-month contract building operational dashboards for a health data co-operative.",
    duties: [
      "Design Power BI datasets and reports for program managers",
      "Tune SQL views feeding the reports",
      "Document data definitions for each report",
    ],
  },
  {
    source: "greenhouse",
    company: 0,
    title: "Senior Data Platform Engineer",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [130_000, 155_000],
    foundDaysAgo: 2,
    review: "new",
    required: ["Python", "Kubernetes", "Terraform", "Spark"],
    preferred: ["Airflow"],
    intro: "Lead the design of Northline's next data platform.",
    duties: [
      "Set platform architecture and standards",
      "Mentor engineers",
      "Run capacity planning",
    ],
  },
  {
    source: "lever",
    company: 4,
    title: "Data Analyst, Operations",
    location: "Edmonton, AB",
    arrangement: "onsite",
    type: "full_time",
    salary: [65_000, 78_000],
    foundDaysAgo: 2,
    review: "new",
    required: ["SQL", "Excel"],
    preferred: ["Power BI", "Tableau"],
    intro:
      "Ravine runs cross-dock freight terminals in Edmonton and Saskatoon.",
    duties: [
      "Report on terminal throughput and on-time performance",
      "Automate weekly Excel reports",
      "Answer ad-hoc questions from operations leads",
    ],
  },
  {
    source: "adzuna",
    company: 5,
    title: "Reporting Analyst",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: null,
    foundDaysAgo: 3,
    review: "new",
    required: ["SQL", "Power BI"],
    preferred: ["Python"],
    intro: "Aspen Grove's member analytics team is hiring a reporting analyst.",
    duties: [
      "Maintain monthly regulatory and member reports",
      "Validate data with finance",
      "Improve report refresh reliability",
    ],
  },
  {
    source: "greenhouse",
    company: 2,
    title: "Data Engineer, Integrations",
    location: "Calgary, AB",
    arrangement: "remote",
    type: "full_time",
    salary: [88_000, 102_000],
    foundDaysAgo: 3,
    review: "shortlisted",
    required: ["Python", "REST APIs", "SQL"],
    preferred: ["PostgreSQL", "Kafka"],
    intro: "Connect Bowridge to clinic billing systems through partner APIs.",
    duties: [
      "Build API connectors with retries and idempotent upserts",
      "Write integration tests against partner sandboxes",
      "Track connector health metrics",
    ],
  },
  {
    source: "lever",
    company: 7,
    title: "Machine Learning Engineer",
    location: "Calgary, AB",
    arrangement: "onsite",
    type: "full_time",
    salary: [120_000, 140_000],
    foundDaysAgo: 4,
    review: "dismissed",
    required: ["Python", "PyTorch", "MLOps"],
    preferred: ["Kubernetes"],
    intro: "Lumen builds demand forecasting for grocery chains.",
    duties: [
      "Train and ship forecasting models",
      "Own model monitoring",
      "Work with data engineering on features",
    ],
  },
  {
    source: "adzuna",
    company: 8,
    title: "Business Intelligence Analyst",
    location: "Edmonton, AB",
    arrangement: "onsite",
    type: "full_time",
    salary: [76_000, 92_000],
    foundDaysAgo: 4,
    review: "shortlisted",
    required: ["Power BI", "SQL", "Excel"],
    preferred: ["Power Automate"],
    intro:
      "Municipal services analytics team supporting transit and waste operations.",
    duties: [
      "Publish service-level dashboards",
      "Automate data collection from operations spreadsheets",
      "Train staff on self-serve reports",
    ],
  },
  {
    source: "greenhouse",
    company: 9,
    title: "Data Engineer (Contract)",
    location: null,
    arrangement: "remote",
    type: "contract",
    salary: [95_000, 115_000],
    foundDaysAgo: 5,
    review: "new",
    required: ["Python", "Airflow", "SQL"],
    preferred: ["dbt", "PostgreSQL"],
    intro:
      "Six-month contract to migrate cron scripts to scheduled Airflow DAGs.",
    duties: [
      "Port existing ingestion scripts to Airflow",
      "Add retries, alerts and run summaries",
      "Hand over runbooks to the internal team",
    ],
  },
  {
    source: "lever",
    company: 3,
    title: "Data Quality Analyst",
    location: "Calgary, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [72_000, 86_000],
    foundDaysAgo: 6,
    review: "new",
    required: ["SQL", "Python"],
    preferred: ["dbt", "Great Expectations"],
    intro: "Help Kestrel trust its numbers.",
    duties: [
      "Write automated checks on policy and claims tables",
      "Triage data incidents",
      "Report quality trends monthly",
    ],
  },
  {
    source: "adzuna",
    company: 6,
    title: "IT Systems Analyst",
    location: "Edmonton, AB",
    arrangement: "onsite",
    type: "full_time",
    salary: [70_000, 82_000],
    foundDaysAgo: 6,
    review: "new",
    required: ["Microsoft 365", "Power Automate"],
    preferred: ["Power BI", "SQL"],
    intro: "Support project systems for a civil construction firm.",
    duties: [
      "Automate project setup in Microsoft 365",
      "Maintain reporting on equipment usage",
      "Support site staff",
    ],
  },
  {
    source: "greenhouse",
    company: 0,
    title: "Analytics Engineer",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [88_000, 104_000],
    foundDaysAgo: 8,
    review: "shortlisted",
    required: ["SQL", "dbt"],
    preferred: ["Python", "Power BI"],
    intro: "Shape the reporting layer field teams rely on every morning.",
    duties: [
      "Model production and maintenance data in dbt",
      "Define shared metrics",
      "Review analysts' SQL",
    ],
  },
  {
    source: "lever",
    company: 4,
    title: "Junior Data Engineer",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [68_000, 80_000],
    foundDaysAgo: 9,
    review: "shortlisted",
    required: ["Python", "SQL"],
    preferred: ["PostgreSQL", "dbt", "Airflow"],
    intro: "First data engineering hire under Ravine's analytics lead.",
    duties: [
      "Build ingestion from terminal systems",
      "Keep the PostgreSQL warehouse tidy",
      "Automate reports that are done by hand today",
    ],
  },
  {
    source: "greenhouse",
    company: 2,
    title: "Data Analyst",
    location: null,
    arrangement: "remote",
    type: "full_time",
    salary: [70_000, 84_000],
    foundDaysAgo: 10,
    review: "shortlisted",
    required: ["SQL", "Python"],
    preferred: ["Looker", "Power BI"],
    intro: "Product analytics for clinic scheduling software.",
    duties: [
      "Analyze feature usage",
      "Build self-serve dashboards",
      "Support experiment readouts",
    ],
  },
  {
    source: "adzuna",
    company: 1,
    title: "Data Engineer",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [82_000, 98_000],
    foundDaysAgo: 11,
    review: "shortlisted",
    required: ["Python", "SQL", "Azure"],
    preferred: ["Azure Data Factory", "Docker"],
    intro:
      "Build pipelines that bring member clinic data into the co-op's Azure warehouse.",
    duties: [
      "Develop Azure Data Factory and Python pipelines",
      "Implement data validation and quarantine",
      "Document lineage for privacy reviews",
    ],
  },
  {
    source: "lever",
    company: 7,
    title: "BI Developer",
    location: "Calgary, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [78_000, 90_000],
    foundDaysAgo: 12,
    review: "shortlisted",
    required: ["Power BI", "SQL"],
    preferred: ["Python", "Tableau"],
    intro: "Retail performance reporting for grocery partners.",
    duties: [
      "Build Power BI reports",
      "Maintain semantic models",
      "Support partner analysts",
    ],
  },
  {
    source: "greenhouse",
    company: 9,
    title: "Platform Support Engineer",
    location: null,
    arrangement: "remote",
    type: "full_time",
    salary: [72_000, 85_000],
    foundDaysAgo: 12,
    review: "dismissed",
    required: ["Linux", "Python"],
    preferred: ["Docker"],
    intro: "Keep Fieldnote's survey platform running for customers.",
    duties: [
      "Investigate customer incidents",
      "Automate support tasks",
      "Improve runbooks",
    ],
  },
  {
    source: "adzuna",
    company: 5,
    title: "Data Engineer",
    location: "Edmonton, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [85_000, 100_000],
    foundDaysAgo: 13,
    review: "shortlisted",
    required: ["SQL", "Python", "PostgreSQL"],
    preferred: ["Airflow"],
    intro: "Modernize member and transaction pipelines at Aspen Grove.",
    duties: [
      "Rebuild nightly loads with tests and monitoring",
      "Design incremental models",
      "Work with security on access controls",
    ],
  },
  {
    source: "lever",
    company: 3,
    title: "Data Engineer",
    location: "Calgary, AB",
    arrangement: "hybrid",
    type: "full_time",
    salary: [92_000, 110_000],
    foundDaysAgo: 13,
    review: "shortlisted",
    required: ["Python", "SQL", "Spark"],
    preferred: ["Airflow", "Snowflake"],
    intro: "Join the claims data platform team.",
    duties: [
      "Build Spark jobs for claims history",
      "Maintain Airflow DAGs",
      "Improve data freshness SLAs",
    ],
  },
  {
    source: "greenhouse",
    company: 2,
    title: "Senior Analytics Engineer",
    location: null,
    arrangement: "remote",
    type: "full_time",
    salary: [125_000, 140_000],
    foundDaysAgo: 7,
    review: "new",
    required: ["SQL", "dbt", "Python"],
    preferred: ["Looker"],
    intro: "Lead the analytics engineering practice at Bowridge.",
    duties: [
      "Set modeling standards",
      "Own the metrics layer",
      "Mentor analysts",
    ],
  },
];

function buildDescription(seed, company) {
  const reqLines = seed.required.map((s) => `Working experience with ${s}`);
  const prefLines = seed.preferred.map((s) => `Exposure to ${s}`);
  const text = [
    seed.intro,
    "",
    "What you'll do",
    ...seed.duties.map((d) => `- ${d}`),
    "",
    "What you bring",
    ...reqLines.map((l) => `- ${l}`),
    "",
    "Nice to have",
    ...prefLines.map((l) => `- ${l}`),
    "",
    `${company.name} is an equal opportunity employer. This is a fictional sample posting.`,
  ].join("\n");
  const skills = [
    ...seed.required.map((name, i) => ({
      name,
      required: true,
      evidence: reqLines[i],
    })),
    ...seed.preferred.map((name, i) => ({
      name,
      required: false,
      evidence: prefLines[i],
    })),
  ];
  return { text, skills };
}

// ---------------------------------------------------------------- scoring
const WEIGHTS = {
  required_skills: 0.4,
  preferred_skills: 0.15,
  title: 0.2,
  location: 0.1,
  work_arrangement: 0.1,
  salary: 0.05,
  experience: 0,
};

const norm = (s) => s.trim().toLowerCase();

/**
 * Explainable baseline score. Each factor scores 0–1, is multiplied by a fixed
 * weight, and carries the evidence shown in the UI. No AI involved.
 */
export function scoreJob(job, profile, now) {
  const mine = new Set(profile.skills.map((s) => norm(s.name)));
  const required = job.skills.filter((s) => s.required);
  const preferred = job.skills.filter((s) => !s.required);
  const has = (s) => mine.has(norm(s.name));
  const reqMatched = required.filter(has);
  const prefMatched = preferred.filter(has);
  const factors = [];
  // A posting with no skills found at all says nothing either way: half marks, not full.
  const unknown = job.skills.length === 0;
  factors.push({
    key: "required_skills",
    label: "Required skills",
    weight: WEIGHTS.required_skills,
    score: unknown
      ? 0.5
      : required.length
        ? reqMatched.length / required.length
        : 1,
    detail: unknown
      ? "No skills found in the posting"
      : required.length
        ? `${reqMatched.length} of ${required.length} required skills on your profile`
        : "No required skills listed",
  });
  factors.push({
    key: "preferred_skills",
    label: "Nice-to-have skills",
    weight: WEIGHTS.preferred_skills,
    score: unknown
      ? 0.5
      : preferred.length
        ? prefMatched.length / preferred.length
        : 1,
    detail: unknown
      ? "No skills found in the posting"
      : preferred.length
        ? `${prefMatched.length} of ${preferred.length} nice-to-have skills`
        : "No nice-to-have skills listed",
  });
  const title = norm(job.title);
  const exactTitle = profile.preferred_titles.find((t) =>
    title.includes(norm(t)),
  );
  const wordOverlap = profile.preferred_titles.find((t) =>
    norm(t)
      .split(/\s+/)
      .some((w) => w.length > 3 && title.split(/\W+/).includes(w)),
  );
  const excluded = profile.exclusions.find((x) => title.includes(norm(x)));
  factors.push({
    key: "title",
    label: "Title",
    weight: WEIGHTS.title,
    score: excluded ? 0 : exactTitle ? 1 : wordOverlap ? 0.5 : 0,
    detail: excluded
      ? `Contains "${excluded}", which is on your exclusion list`
      : exactTitle
        ? `Matches your target title "${exactTitle}"`
        : wordOverlap
          ? `Related to your target title "${wordOverlap}"`
          : "Not one of your target titles",
  });
  const city = (loc) => norm(loc.split(",")[0]);
  const remote = job.work_arrangement === "remote";
  const remoteOpen =
    remote && remoteOpenToYou(job.location, userArea(profile.locations));
  const locMatch =
    remoteOpen ||
    (job.location != null &&
      profile.locations.some((l) => city(l) === city(job.location)));
  factors.push({
    key: "location",
    label: "Location",
    weight: WEIGHTS.location,
    score: locMatch ? 1 : 0,
    detail: remoteOpen
      ? "Remote, so location doesn't limit you"
      : remote && !locMatch
        ? `Remote, but only for people in ${job.location}`
        : locMatch
          ? `${job.location} is one of your locations`
          : `${job.location ?? "Location not stated"} is outside your locations`,
  });
  const arrangementOk =
    job.work_arrangement !== "unknown" &&
    profile.work_arrangements.includes(job.work_arrangement);
  factors.push({
    key: "work_arrangement",
    label: "Work arrangement",
    weight: WEIGHTS.work_arrangement,
    score: job.work_arrangement === "unknown" ? 0.5 : arrangementOk ? 1 : 0,
    detail:
      job.work_arrangement === "unknown"
        ? "Arrangement not stated in the posting"
        : arrangementOk
          ? "Matches a work arrangement you accept"
          : "Not a work arrangement you selected",
  });
  let salaryScore = 0.5;
  let salaryDetail = "Salary not posted";
  if (job.salary_max != null && profile.salary_min != null) {
    salaryScore = job.salary_max >= profile.salary_min ? 1 : 0;
    salaryDetail =
      salaryScore === 1
        ? "Posted range reaches your minimum"
        : "Posted range tops out below your minimum";
  }
  factors.push({
    key: "salary",
    label: "Salary",
    weight: WEIGHTS.salary,
    score: salaryScore,
    detail: salaryDetail,
  });
  const total = factors.reduce((sum, f) => sum + f.weight * f.score, 0);
  const score = Math.round(total * 100);
  const missing = [...required, ...preferred]
    .filter((s) => !has(s))
    .map((s) => s.name);
  const missingRequired = required.filter((s) => !has(s)).map((s) => s.name);
  return {
    job_id: job.id,
    score,
    summary: unknown
      ? "No skills found in the posting; read it to judge the fit."
      : missingRequired.length === 0
        ? "You have every required skill listed."
        : `Missing ${missingRequired.length} required skill${missingRequired.length === 1 ? "" : "s"}: ${missingRequired.join(", ")}.`,
    factors,
    matched_skills: [...reqMatched, ...prefMatched].map((s) => s.name),
    missing_skills: missing,
    method: "rules",
    computed_at: now.toISOString(),
  };
}

// ---------------------------------------------------------------- jobs
export function createJobs(now, profile) {
  return JOB_SEEDS.map((seed, i) => {
    const company = COMPANIES[seed.company];
    const { text, skills } = buildDescription(seed, company);
    const id = `job_${String(i + 1).padStart(3, "0")}`;
    const firstSeen = daysAgoIso(now, seed.foundDaysAgo, 6, 15 + (i % 40));
    const job = {
      id,
      source: seed.source,
      source_job_id: `${seed.source}-${4100 + i * 7}`,
      title: seed.title,
      company,
      location: seed.location,
      work_arrangement: seed.arrangement,
      employment_type: seed.type,
      description: text,
      url: `https://jobs.example.com/${company.id.replace("co_", "")}/${4100 + i * 7}`,
      salary_min: seed.salary?.[0] ?? null,
      salary_max: seed.salary?.[1] ?? null,
      salary_currency: seed.salary ? "CAD" : null,
      posted_at: daysAgoIso(now, seed.foundDaysAgo + (i % 3), 12),
      first_seen_at: firstSeen,
      last_seen_at: daysAgoIso(now, 0, 6, 15),
      review_status: seed.review,
      skills,
      match: null,
      application_id: null,
    };
    job.match = scoreJob(job, profile, now);
    return job;
  });
}

const APP_SEEDS = [
  {
    job: 3,
    status: "preparing",
    createdDaysAgo: 1,
    path: ["saved", "preparing"],
    notes: "Contract role — ask about extension.",
    resume: "doc_003",
  },
  {
    job: 7,
    status: "ready_for_review",
    createdDaysAgo: 3,
    path: ["saved", "preparing", "ready_for_review"],
    notes: "Highlight the API connector work.",
    resume: "doc_003",
    cover: "doc_005",
  },
  { job: 9, status: "saved", createdDaysAgo: 4, path: ["saved"], notes: "" },
  {
    job: 13,
    status: "applied",
    createdDaysAgo: 8,
    appliedDaysAgo: 7,
    path: ["saved", "preparing", "ready_for_review", "applied"],
    notes: "Referred by a former classmate.",
    resume: "doc_003",
    cover: "doc_004",
  },
  {
    job: 14,
    status: "interview",
    createdDaysAgo: 9,
    appliedDaysAgo: 9,
    path: ["saved", "preparing", "applied", "interview"],
    notes: "Hiring manager is the analytics lead.",
    resume: "doc_002",
    interview: {
      inDays: 2,
      format: "video",
      with: "Analytics lead and one engineer",
    },
  },
  {
    job: 15,
    status: "applied",
    createdDaysAgo: 10,
    appliedDaysAgo: 16,
    path: ["saved", "applied"],
    notes: "Applied on their site before tracking here.",
    resume: "doc_002",
  },
  {
    job: 16,
    status: "rejected",
    createdDaysAgo: 11,
    appliedDaysAgo: 11,
    path: ["saved", "preparing", "applied", "rejected"],
    notes:
      "Rejection email said they chose someone with Azure Data Factory experience.",
    resume: "doc_002",
  },
  {
    job: 17,
    status: "withdrawn",
    createdDaysAgo: 12,
    path: ["saved", "preparing", "withdrawn"],
    notes: "Role moved to Calgary on-site full time.",
  },
  {
    job: 19,
    status: "offer",
    createdDaysAgo: 13,
    appliedDaysAgo: 13,
    path: [
      "saved",
      "preparing",
      "ready_for_review",
      "applied",
      "interview",
      "offer",
    ],
    notes: "Offer call scheduled. Compare with the Bowridge process.",
    resume: "doc_002",
    cover: "doc_004",
  },
];
let eventCounter = 0;

function evt(
  applicationId,
  occurredAt,
  type,
  summary,
  from = null,
  to = null,
  interview = null,
) {
  eventCounter += 1;
  return {
    id: `evt_${String(eventCounter).padStart(4, "0")}`,
    application_id: applicationId,
    event_type: type,
    occurred_at: occurredAt,
    summary,
    from_status: from,
    to_status: to,
    interview,
  };
}

export function createApplications(now, jobs) {
  eventCounter = 0;
  return APP_SEEDS.map((seed, i) => {
    const job = jobs[seed.job];
    const id = `app_${String(i + 1).padStart(3, "0")}`;
    job.application_id = id;
    const events = [];
    const created = daysAgoIso(now, seed.createdDaysAgo, 19);
    events.push(
      evt(id, created, "created", "Application created", null, "saved"),
    );
    // Spread the status path between creation and today.
    const steps = seed.path.slice(1);
    steps.forEach((to, step) => {
      const from = seed.path[step];
      const daysAgo = Math.max(
        0,
        Math.round(
          seed.createdDaysAgo -
            ((step + 1) * seed.createdDaysAgo) / (steps.length + 1),
        ),
      );
      const at = daysAgoIso(now, daysAgo, 20, step * 5);
      if (to === "applied") {
        events.push(
          evt(
            id,
            at,
            "submission_confirmed",
            "You confirmed you submitted this application on the employer's site",
            from,
            "applied",
          ),
        );
      } else {
        events.push(
          evt(
            id,
            at,
            "status_changed",
            `Status changed to ${to.replaceAll("_", " ")}`,
            from,
            to,
          ),
        );
      }
    });
    if (seed.interview) {
      const when = new Date(now);
      when.setDate(when.getDate() + seed.interview.inDays);
      when.setHours(10, 0, 0, 0);
      events.push(
        evt(
          id,
          daysAgoIso(now, 1, 15),
          "interview_scheduled",
          `${seed.interview.format[0].toUpperCase()}${seed.interview.format.slice(1)} interview scheduled`,
          null,
          null,
          {
            scheduled_for: when.toISOString(),
            format: seed.interview.format,
            with_whom: seed.interview.with,
          },
        ),
      );
    }
    const appliedAt =
      seed.appliedDaysAgo != null
        ? daysAgoDate(now, seed.appliedDaysAgo)
        : null;
    const followUp =
      appliedAt && (seed.status === "applied" || seed.status === "interview")
        ? addDays(appliedAt, 14)
        : null;
    events.sort((a, b) => b.occurred_at.localeCompare(a.occurred_at));
    return {
      id,
      job_id: job.id,
      job: {
        title: job.title,
        company_name: job.company.name,
        location: job.location,
        url: job.url,
        source: job.source,
      },
      status: seed.status,
      status_source: "user",
      applied_at: appliedAt,
      follow_up_at: followUp,
      resume_document_id: seed.resume ?? null,
      cover_letter_document_id: seed.cover ?? null,
      notes: seed.notes,
      created_at: created,
      updated_at: events[0].occurred_at,
      events,
    };
  });
}

// ---------------------------------------------------------------- documents
export function createDocuments(now, jobs) {
  const j = (i) => jobs[i];
  return [
    {
      id: "doc_001",
      document_type: "resume",
      title: "General résumé",
      version: 1,
      status: "archived",
      origin: "uploaded",
      related_job_id: null,
      related_job_title: null,
      file_name: "jordan-lee-resume-v1.pdf",
      size_bytes: 148_220,
      created_at: daysAgoIso(now, 60),
      updated_at: daysAgoIso(now, 30),
    },
    {
      id: "doc_002",
      document_type: "resume",
      title: "Data-focused résumé",
      version: 2,
      status: "ready",
      origin: "uploaded",
      related_job_id: null,
      related_job_title: null,
      file_name: "jordan-lee-resume-data.pdf",
      size_bytes: 152_904,
      created_at: daysAgoIso(now, 30),
      updated_at: daysAgoIso(now, 30),
    },
    {
      id: "doc_003",
      document_type: "resume",
      title: "Data-focused résumé (pipelines first)",
      version: 3,
      status: "ready",
      origin: "uploaded",
      related_job_id: null,
      related_job_title: null,
      file_name: "jordan-lee-resume-data-v3.pdf",
      size_bytes: 155_310,
      created_at: daysAgoIso(now, 6),
      updated_at: daysAgoIso(now, 6),
    },
    {
      id: "doc_004",
      document_type: "cover_letter",
      title: `Cover letter — ${j(13).company.name}`,
      version: 1,
      status: "ready",
      origin: "generated",
      related_job_id: j(13).id,
      related_job_title: j(13).title,
      file_name: null,
      size_bytes: null,
      created_at: daysAgoIso(now, 8),
      updated_at: daysAgoIso(now, 7),
    },
    {
      id: "doc_005",
      document_type: "cover_letter",
      title: `Cover letter — ${j(7).company.name}`,
      version: 1,
      status: "draft",
      origin: "generated",
      related_job_id: j(7).id,
      related_job_title: j(7).title,
      file_name: null,
      size_bytes: null,
      created_at: daysAgoIso(now, 2),
      updated_at: daysAgoIso(now, 2),
    },
    {
      id: "doc_006",
      document_type: "cover_letter",
      title: `Cover letter — ${j(3).company.name}`,
      version: 1,
      status: "draft",
      origin: "generated",
      related_job_id: j(3).id,
      related_job_title: j(3).title,
      file_name: null,
      size_bytes: null,
      created_at: daysAgoIso(now, 1),
      updated_at: daysAgoIso(now, 1),
    },
  ];
}

// ---------------------------------------------------------------- settings
export function createSettings(now) {
  return {
    sources: [
      {
        source: "greenhouse",
        enabled: true,
        identifiers: ["northline", "bowridge", "fieldnote"],
        last_run_at: daysAgoIso(now, 0, 6, 15),
        last_run_status: "succeeded",
        last_run_summary: {
          fetched: 214,
          inserted: 3,
          updated: 11,
          skipped: 200,
          failed: 0,
        },
        credentials_configured: true,
      },
      {
        source: "lever",
        enabled: true,
        identifiers: ["kestrel", "ravine", "lumen"],
        last_run_at: daysAgoIso(now, 0, 6, 16),
        last_run_status: "partial",
        last_run_summary: {
          fetched: 96,
          inserted: 1,
          updated: 4,
          skipped: 89,
          failed: 2,
        },
        credentials_configured: true,
      },
      {
        source: "adzuna",
        enabled: true,
        identifiers: ["data engineer", "bi developer", "data analyst"],
        last_run_at: daysAgoIso(now, 0, 6, 18),
        last_run_status: "succeeded",
        last_run_summary: {
          fetched: 50,
          inserted: 2,
          updated: 6,
          skipped: 42,
          failed: 0,
        },
        credentials_configured: true,
      },
    ],
    notifications: {
      daily_digest: true,
      digest_hour: 7,
      digest_min_score: 70,
      follow_up_reminders: true,
    },
    account: {
      display_name: "Jordan",
      email: "jordan.lee@example.com",
      timezone: "America/Edmonton",
    },
  };
}

// ---------------------------------------------------------------- database
export function createMockDatabase(now = new Date()) {
  const profile = createProfile(now);
  const jobs = createJobs(now, profile);
  const applications = createApplications(now, jobs);
  const documents = createDocuments(now, jobs);
  return {
    jobs,
    applications,
    documents,
    profile,
    settings: createSettings(now),
  };
}

export function createEmptyDatabase(now = new Date()) {
  const profile = createProfile(now);
  return {
    jobs: [],
    applications: [],
    documents: [],
    profile: {
      ...profile,
      summary: "",
      headline: "",
      skills: [],
      experience: [],
      education: [],
    },
    settings: {
      ...createSettings(now),
      sources: createSettings(now).sources.map((s) => ({
        ...s,
        last_run_at: null,
        last_run_status: "never",
        last_run_summary: null,
      })),
    },
  };
}
