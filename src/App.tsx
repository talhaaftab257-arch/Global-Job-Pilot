import React, { useEffect, useMemo, useState } from 'react';
import {
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams
} from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  ChartNoAxesCombined,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Globe2,
  Home,
  Menu,
  Search,
  Settings as SettingsIcon,
  ShieldCheck,
  SlidersHorizontal,
  X,
  Bell,
  MapPin,
  ExternalLink,
  RefreshCw,
  Plus,
  Send,
  Database,
  Bookmark,
  Filter,
  CheckCircle2,
  Calendar,
  DollarSign,
  FileText,
  UserCheck,
  Award
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import { supabase } from './lib/supabase';
import type { Job } from './types';

const NAV_ITEMS = [
  ['Dashboard', '/', Home],
  ['All Jobs', '/jobs', BriefcaseBusiness],
  ['Sponsorship Tracker', '/sponsorship', ShieldCheck],
  ['Countries', '/countries', Globe2],
  ['Applications', '/applications', ClipboardList],
  ['Sources', '/sources', Database],
  ['Preferences', '/preferences', SlidersHorizontal],
  ['Settings', '/settings', SettingsIcon]
] as const;

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function App() {
  const [drawer, setDrawer] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [saved, setSaved] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [notice, setNotice] = useState('');
  const navigate = useNavigate();

  const flash = (msg: string) => {
    setNotice(msg);
    setTimeout(() => setNotice(''), 4000);
  };

  const loadJobs = () => {
    setLoading(true);
    fetch(`${API_BASE}/api/jobs?limit=500`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('Failed to load jobs'))))
      .then((data) => {
        setJobs(data.items ?? []);
        setError('');
        setLoading(false);
      })
      .catch(() => {
        setError('Backend API is not available. Ensure FastAPI is running on port 8000.');
        setLoading(false);
      });
  };

  useEffect(() => {
    loadJobs();
    // Load existing saved application IDs
    fetch(`${API_BASE}/api/applications`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((res) => {
        if (res.items) {
          setSaved(res.items.map((a: any) => a.job_id));
        }
      })
      .catch(() => {});
  }, []);

  const triggerRun = async () => {
    setRunning(true);
    try {
      const res = await fetch(`${API_BASE}/api/collect/run`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        flash(`Search finished: ${data.discovered} discovered, ${data.saved} new saved.`);
        loadJobs();
      } else {
        flash('Collection request failed. Check server status.');
      }
    } catch {
      flash('Unable to connect to collection backend.');
    } finally {
      setRunning(false);
    }
  };

  const toggleSave = async (jobId: string) => {
    const isSaved = saved.includes(jobId);
    const newSaved = isSaved ? saved.filter((id) => id !== jobId) : [...saved, jobId];
    setSaved(newSaved);

    try {
      if (!isSaved) {
        await fetch(`${API_BASE}/api/applications`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId, status: 'saved' })
        });
        flash('Job saved to your Applications list.');
      }
    } catch {
      // Keep local state
    }
  };

  // Global search filtering
  const filteredJobs = useMemo(() => {
    if (!query.trim()) return jobs;
    const q = query.toLowerCase();
    return jobs.filter(
      (j) =>
        j.title.toLowerCase().includes(q) ||
        j.company.toLowerCase().includes(q) ||
        (j.location && j.location.toLowerCase().includes(q)) ||
        (j.country && j.country.toLowerCase().includes(q)) ||
        (j.required_skills && j.required_skills.some((s) => s.toLowerCase().includes(q)))
    );
  }, [jobs, query]);

  return (
    <div className="shell">
      {/* Sidebar */}
      <aside className={`sidebar ${drawer ? 'open' : ''}`}>
        <div className="brand">
          <div className="brandmark">
            <Building2 size={24} />
          </div>
          <div>
            <b>
              Global AI
              <br />
              JobPilot
            </b>
            <small>Find. Apply. Relocate.</small>
          </div>
          <button className="close-drawer" onClick={() => setDrawer(false)}>
            <X size={18} />
          </button>
        </div>

        <nav>
          {NAV_ITEMS.map(([label, path, Icon]) => (
            <NavLink
              key={path}
              to={path}
              onClick={() => setDrawer(false)}
              className={({ isActive }) => `navitem ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="run-card">
          <div className="run-label">
            <span className="pulse" />
            Next Scheduled Run
          </div>
          <p>Daily at 03:00 UTC (GitHub Actions)</p>
          <button onClick={triggerRun} disabled={running}>
            <Send size={14} />
            {running ? 'Collecting…' : 'Run Collection Now'}
          </button>
        </div>

        <div className="profile">
          <div className="avatar">TA</div>
          <div>
            <b>Talha Aftab</b>
            <small>Lead Data Scientist / AI &bull; PK</small>
          </div>
          <ChevronDown size={14} />
        </div>
      </aside>

      {drawer && <div className="scrim" onClick={() => setDrawer(false)} />}

      {/* Main Workspace */}
      <main className="main">
        <header className="topbar">
          <button className="mobile-menu iconbtn" onClick={() => setDrawer(true)}>
            <Menu size={20} />
          </button>
          <label className="global-search">
            <Search size={18} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search jobs, companies, skills, or countries... (e.g. 'Anthropic', 'LangGraph', 'Germany')"
            />
            <kbd>⌘ K</kbd>
          </label>
          <button
            className="iconbtn notification"
            onClick={() => flash('Daily report delivered at 03:00 UTC.')}
            title="Notifications"
          >
            <Bell size={18} />
            <i />
          </button>
          <button className="upgrade" onClick={() => navigate('/preferences')}>
            <ArrowUpRight size={15} /> Preferences
          </button>
        </header>

        <div className="content">
          {notice && (
            <div className="toast">
              <span>{notice}</span>
              <button onClick={() => setNotice('')}>
                <X size={14} />
              </button>
            </div>
          )}

          <Routes>
            <Route
              path="/"
              element={
                <Dashboard
                  jobs={filteredJobs}
                  loading={loading}
                  error={error}
                  navigate={navigate}
                  saved={saved}
                  toggleSaved={toggleSave}
                />
              }
            />
            <Route
              path="/jobs"
              element={
                <JobsScreen
                  jobs={filteredJobs}
                  loading={loading}
                  saved={saved}
                  toggleSaved={toggleSave}
                  navigate={navigate}
                />
              }
            />
            <Route
              path="/job/:id"
              element={
                <JobDetailScreen
                  jobs={jobs}
                  saved={saved}
                  toggleSaved={toggleSave}
                  navigate={navigate}
                  flash={flash}
                />
              }
            />
            <Route
              path="/sponsorship"
              element={
                <SponsorshipScreen
                  jobs={filteredJobs}
                  saved={saved}
                  toggleSaved={toggleSave}
                  navigate={navigate}
                />
              }
            />
            <Route
              path="/countries"
              element={<CountriesScreen jobs={jobs} navigate={navigate} />}
            />
            <Route
              path="/applications"
              element={<ApplicationsScreen jobs={jobs} flash={flash} navigate={navigate} />}
            />
            <Route
              path="/sources"
              element={<SourcesScreen onRefresh={triggerRun} running={running} flash={flash} />}
            />
            <Route path="/preferences" element={<PreferencesScreen flash={flash} />} />
            <Route path="/settings" element={<SettingsScreen flash={flash} />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

// -------------------------------------------------------------
// Component: Stat Card
// -------------------------------------------------------------
function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color
}: {
  icon: any;
  label: string;
  value: string;
  trend: string;
  color: string;
}) {
  return (
    <div className="stat card">
      <div className="stat-head">
        <span className={`stat-icon ${color}`}>
          <Icon size={17} />
        </span>
        <span className="trend">
          <ArrowUpRight size={12} />
          {trend}
        </span>
      </div>
      <strong>{value}</strong>
      <span className="muted">{label}</span>
      <div className={`spark ${color}`}>
        <AreaChart
          width={110}
          height={26}
          data={[
            { v: 5 },
            { v: 7 },
            { v: 6 },
            { v: 10 },
            { v: 8 },
            { v: 14 },
            { v: 12 },
            { v: 16 }
          ]}
        >
          <Area
            dataKey="v"
            stroke="currentColor"
            fill="none"
            strokeWidth={2}
            isAnimationActive={false}
          />
        </AreaChart>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Component: Badge
// -------------------------------------------------------------
function Badge({ status }: { status: Job['sponsorship_status'] }) {
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unverified';
  return (
    <span className={`badge ${status || 'unverified'}`}>
      <span />
      {label}
    </span>
  );
}

// -------------------------------------------------------------
// Component: Job Row
// -------------------------------------------------------------
function JobRow({
  job,
  navigate,
  saved,
  toggleSaved
}: {
  job: Job;
  navigate: (s: string) => void;
  saved: boolean;
  toggleSaved: (id: string) => void;
}) {
  const logoLetter = (job.company || 'J').charAt(0).toUpperCase();
  const loc = [job.location, job.country].filter(Boolean).join(', ') || 'Location not specified';

  return (
    <article className="job-row">
      <div className="company-logo">{logoLetter}</div>
      <div className="job-main">
        <button
          className="job-title"
          onClick={() => navigate(`/job/${job.id}`)}
          title={job.title}
        >
          {job.title}
        </button>
        <span className="company">{job.company}</span>
        <span className="location">
          <MapPin size={11} />
          {loc}
        </span>
        <div className="tags">
          {(job.required_skills || []).slice(0, 4).map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      </div>
      <div className="job-status">
        <Badge status={job.sponsorship_status} />
        <b>
          {job.match_score ?? '—'}
          <small>{job.match_score ? '% Match' : ' Match'}</small>
        </b>
      </div>
      <button
        className={`save-btn ${saved ? 'saved' : ''}`}
        aria-label="Save job"
        onClick={() => toggleSaved(job.id)}
        title={saved ? 'Job Saved' : 'Save Job'}
      >
        <Bookmark size={16} />
      </button>
      <a
        className="apply-btn"
        href={job.application_url}
        target="_blank"
        rel="noreferrer"
      >
        Apply <ArrowRight size={13} />
      </a>
    </article>
  );
}

// -------------------------------------------------------------
// SCREEN 1: Dashboard
// -------------------------------------------------------------
function Dashboard({
  jobs,
  loading,
  error,
  navigate,
  saved,
  toggleSaved
}: {
  jobs: Job[];
  loading: boolean;
  error: string;
  navigate: (s: string) => void;
  saved: string[];
  toggleSaved: (id: string) => void;
}) {
  const counts = {
    confirmed: jobs.filter((j) => j.sponsorship_status === 'confirmed').length,
    likely: jobs.filter((j) => j.sponsorship_status === 'likely').length,
    unverified: jobs.filter((j) => j.sponsorship_status === 'unverified').length,
    unavailable: jobs.filter((j) => j.sponsorship_status === 'unavailable').length
  };

  const avgMatch = jobs.length
    ? Math.round(jobs.reduce((acc, j) => acc + (j.match_score ?? 0), 0) / jobs.length)
    : 0;
  const matchingJobs = jobs.filter((j) => (j.match_score ?? 0) >= 70).length;
  const countriesCount = new Set(jobs.map((j) => j.country).filter(Boolean)).size;

  const regions = [
    { name: 'North America', v: 48, color: '#00bf91' },
    { name: 'Europe', v: 36, color: '#2488f5' },
    { name: 'Asia-Pacific', v: 10, color: '#b548a0' },
    { name: 'Middle East', v: 4, color: '#ff944d' },
    { name: 'Other', v: 2, color: '#8898aa' }
  ];

  return (
    <>
      <section className="hero">
        <div className="hero-orb" />
        <div className="hero-copy">
          <span className="eyebrow">GLOBAL OPPORTUNITY INTELLIGENCE</span>
          <h1>
            Your Global AI Career,
            <br />
            One Smart Platform
          </h1>
          <p>
            Discover visa sponsorship jobs worldwide with intelligent candidate matching.
          </p>
          <button className="primary" onClick={() => navigate('/jobs')}>
            Explore Latest Opportunities <ArrowRight size={15} />
          </button>
        </div>
        <div className="hero-checks">
          {['Visa Sponsorship', 'Worldwide Jobs', 'AI-Powered Matching', 'Daily Updates'].map(
            (x) => (
              <span key={x}>
                <Check size={13} />
                {x}
              </span>
            )
          )}
        </div>
        <Globe2 className="hero-globe" size={210} />
      </section>

      {/* Top 5 Metrics */}
      <div className="stats">
        <StatCard
          icon={BriefcaseBusiness}
          label="Total Jobs Found"
          value={String(jobs.length)}
          trend="Live"
          color="blue"
        />
        <StatCard
          icon={ChartNoAxesCombined}
          label="Matching Jobs (≥70%)"
          value={String(matchingJobs)}
          trend="Live"
          color="teal"
        />
        <StatCard
          icon={ShieldCheck}
          label="Sponsorship Jobs"
          value={String(counts.confirmed + counts.likely)}
          trend="Live"
          color="green"
        />
        <StatCard
          icon={Activity}
          label="Avg Match Score"
          value={jobs.length ? `${avgMatch}%` : '—'}
          trend="Live"
          color="purple"
        />
        <StatCard
          icon={Globe2}
          label="Countries"
          value={String(countriesCount)}
          trend="Live"
          color="blue"
        />
      </div>

      {/* Dashboard Middle Grid */}
      <div className="dash-grid">
        <section className="card jobs-panel">
          <div className="section-head">
            <h2>
              <span className="tiny-icon">
                <BriefcaseBusiness size={15} />
              </span>
              Top Matched Jobs for You
            </h2>
            <button className="textbtn" onClick={() => navigate('/jobs')}>
              View All <ArrowRight size={13} />
            </button>
          </div>
          {loading ? (
            <div className="empty">
              <RefreshCw className="spin" size={20} />
              <p>Loading real job opportunities…</p>
            </div>
          ) : error ? (
            <div className="empty">{error}</div>
          ) : jobs.length ? (
            jobs
              .slice(0, 6)
              .map((j) => (
                <JobRow
                  key={j.id}
                  job={j}
                  navigate={navigate}
                  saved={saved.includes(j.id)}
                  toggleSaved={toggleSaved}
                />
              ))
          ) : (
            <div className="empty-state">
              <Search size={24} />
              <h3>No jobs collected yet</h3>
              <p>Click "Run Collection Now" to fetch live AI engineering opportunities.</p>
            </div>
          )}
        </section>

        {/* Right Stack: Charts */}
        <div className="right-stack">
          <section className="card chart-card">
            <div className="section-head">
              <h2>
                <Globe2 size={16} />
                Job Distribution
              </h2>
              <span className="small-select">
                By Region <ChevronDown size={12} />
              </span>
            </div>
            {jobs.length ? (
              <div className="chart-content">
                <div className="donut">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={regions}
                        dataKey="v"
                        innerRadius="68%"
                        outerRadius="94%"
                        paddingAngle={3}
                      >
                        {regions.map((r) => (
                          <Cell key={r.name} fill={r.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-center">
                    <b>{jobs.length}</b>
                    <small>Jobs</small>
                  </div>
                </div>
                <div className="legend">
                  {regions.map((r) => (
                    <div key={r.name}>
                      <i style={{ background: r.color }} />
                      <span>{r.name}</span>
                      <b>{r.v}%</b>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty compact">Distribution appears after collection.</div>
            )}
          </section>

          <section className="card sponsor-card">
            <div className="section-head">
              <h2>
                <ShieldCheck size={16} />
                Sponsorship Breakdown
              </h2>
              <button className="textbtn" onClick={() => navigate('/sponsorship')}>
                View Details <ArrowRight size={13} />
              </button>
            </div>
            <div className="statusbar">
              <span
                style={{
                  flex: Math.max(counts.confirmed, 1),
                  background: '#04c38a'
                }}
                title={`Confirmed: ${counts.confirmed}`}
              />
              <span
                style={{ flex: Math.max(counts.likely, 1), background: '#51abf5' }}
                title={`Likely: ${counts.likely}`}
              />
              <span
                style={{
                  flex: Math.max(counts.unverified, 1),
                  background: '#dfe6ef'
                }}
                title={`Unverified: ${counts.unverified}`}
              />
              <span
                style={{
                  flex: Math.max(counts.unavailable, 1),
                  background: '#ff6565'
                }}
                title={`Unavailable: ${counts.unavailable}`}
              />
            </div>
            <div className="statuslabels">
              <span>
                Confirmed<b>{counts.confirmed}</b>
              </span>
              <span>
                Likely<b>{counts.likely}</b>
              </span>
              <span>
                Unverified<b>{counts.unverified}</b>
              </span>
              <span>
                Unavailable<b>{counts.unavailable}</b>
              </span>
            </div>
          </section>
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="bottom-grid">
        <section className="card activity-card">
          <h2>
            <Activity size={16} />
            Recent Activity
          </h2>
          <div className="activity-line">
            <i />
            <span>Automated pipeline connected to public employer feeds</span>
          </div>
          <div className="activity-line">
            <i />
            <span>
              <strong>{jobs.length}</strong> real jobs normalized & indexed
            </span>
          </div>
          <div className="activity-line">
            <i />
            <span>Scheduled daily run configured at 03:00 UTC</span>
          </div>
        </section>

        <section className="card glance">
          <h2>
            <ChartNoAxesCombined size={16} />
            Your Job Search at a Glance
          </h2>
          <div className="glance-value">
            {jobs.length ? `${avgMatch}% Average Match Score` : 'Ready to begin search'}
          </div>
          <p>Scored against your Lead Data Scientist & AI Engineer skills profile.</p>
          <div className="glance-graphic">
            <AreaChart
              width={260}
              height={50}
              data={[
                { v: 12 },
                { v: 22 },
                { v: 18 },
                { v: 36 },
                { v: 30 },
                { v: 52 },
                { v: 48 },
                { v: 64 }
              ]}
            >
              <Area
                dataKey="v"
                stroke="#00bd91"
                fill="#e5f8f2"
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </div>
        </section>

        <section className="cta">
          <span>✦ READY FOR YOUR NEXT MOVE?</span>
          <h2>
            Let JobPilot find the
            <br />
            right role for you.
          </h2>
          <button onClick={() => navigate('/preferences')}>
            Update Preferences <ArrowRight size={13} />
          </button>
        </section>
      </div>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 2: All Jobs
// -------------------------------------------------------------
function JobsScreen({
  jobs,
  loading,
  saved,
  toggleSaved,
  navigate
}: {
  jobs: Job[];
  loading: boolean;
  saved: string[];
  toggleSaved: (id: string) => void;
  navigate: (s: string) => void;
}) {
  const [sponsorship, setSponsorship] = useState('all');
  const [country, setCountry] = useState('all');
  const [sort, setSort] = useState('match');
  const [localQuery, setLocalQuery] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const uniqueCountries = useMemo(
    () => Array.from(new Set(jobs.map((j) => j.country).filter(Boolean) as string[])).sort(),
    [jobs]
  );

  const filtered = useMemo(() => {
    return jobs
      .filter((j) => {
        if (sponsorship !== 'all' && j.sponsorship_status !== sponsorship) return false;
        if (country !== 'all' && j.country !== country) return false;
        if (localQuery.trim()) {
          const q = localQuery.toLowerCase();
          const haystack = `${j.title} ${j.company} ${j.location || ''} ${(j.required_skills || []).join(' ')}`.toLowerCase();
          if (!haystack.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sort === 'match') return (b.match_score ?? 0) - (a.match_score ?? 0);
        return new Date(b.posted_at ?? 0).getTime() - new Date(a.posted_at ?? 0).getTime();
      });
  }, [jobs, sponsorship, country, localQuery, sort]);

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">GLOBAL AI JOB SEARCH</span>
          <h1>Discover Worldwide AI Jobs</h1>
          <p>
            Showing {filtered.length} curated opportunities matching your engineering profile.
          </p>
        </div>
      </div>

      <div className="toolbar card">
        <div className="filter-search">
          <Search size={16} />
          <input
            value={localQuery}
            onChange={(e) => {
              setLocalQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Filter by title, company, or skill…"
          />
        </div>

        <select
          value={sponsorship}
          onChange={(e) => {
            setSponsorship(e.target.value);
            setPage(1);
          }}
        >
          <option value="all">All Sponsorship</option>
          <option value="confirmed">Confirmed Sponsorship</option>
          <option value="likely">Likely Sponsorship</option>
          <option value="unverified">Unverified</option>
          <option value="unavailable">Unavailable</option>
        </select>

        <select
          value={country}
          onChange={(e) => {
            setCountry(e.target.value);
            setPage(1);
          }}
        >
          <option value="all">All Countries</option>
          {uniqueCountries.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(e) => {
            setSort(e.target.value);
            setPage(1);
          }}
        >
          <option value="match">Best Match Score</option>
          <option value="date">Most Recently Posted</option>
        </select>

        <button
          className="outline"
          onClick={() => {
            setSponsorship('all');
            setCountry('all');
            setLocalQuery('');
            setSort('match');
            setPage(1);
          }}
        >
          <Filter size={14} /> Reset
        </button>
      </div>

      <div className="list-card card">
        {loading ? (
          <div className="empty">
            <RefreshCw className="spin" size={20} />
            <p>Loading jobs…</p>
          </div>
        ) : paginated.length ? (
          paginated.map((j) => (
            <JobRow
              key={j.id}
              job={j}
              navigate={navigate}
              saved={saved.includes(j.id)}
              toggleSaved={toggleSaved}
            />
          ))
        ) : (
          <div className="empty-state">
            <Search size={22} />
            <h3>No matching jobs found</h3>
            <p>Try adjusting your filters or search keywords.</p>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16 }}>
          <button
            className="outline"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <span style={{ fontSize: 12, color: '#657490' }}>
            Page {page} of {totalPages}
          </span>
          <button
            className="outline"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      )}
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 3: Job Details
// -------------------------------------------------------------
function JobDetailScreen({
  jobs,
  saved,
  toggleSaved,
  navigate,
  flash
}: {
  jobs: Job[];
  saved: string[];
  toggleSaved: (id: string) => void;
  navigate: (s: string) => void;
  flash: (s: string) => void;
}) {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [tab, setTab] = useState<'overview' | 'requirements' | 'sponsorship' | 'fit'>('overview');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const existing = jobs.find((j) => j.id === id);
    if (existing) {
      setJob(existing);
      setLoading(false);
    } else if (id) {
      fetch(`${API_BASE}/api/jobs/${id}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          setJob(data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [id, jobs]);

  if (loading) {
    return (
      <div className="empty">
        <RefreshCw className="spin" size={20} />
        <p>Loading job details…</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="empty-state">
        <BriefcaseBusiness size={24} />
        <h3>Job not found</h3>
        <p>This vacancy may have been updated or removed.</p>
        <button className="primary" onClick={() => navigate('/jobs')}>
          Back to All Jobs
        </button>
      </div>
    );
  }

  const isSaved = saved.includes(job.id);
  const loc = [job.location, job.country].filter(Boolean).join(', ') || 'Location not listed';

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <button className="textbtn" onClick={() => navigate('/jobs')}>
          <ChevronLeft size={14} /> Back to All Jobs
        </button>
      </div>

      <section className="card detail">
        <div className="detail-top">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <Badge status={job.sponsorship_status} />
              <span style={{ fontSize: 12, fontWeight: 700, color: '#00a875' }}>
                {job.match_score}% Profile Match
              </span>
            </div>
            <h2>{job.title}</h2>
            <p>
              <Building2 size={13} /> {job.company} &bull; <MapPin size={13} /> {loc}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className={`outline ${isSaved ? 'saved' : ''}`}
              onClick={() => toggleSaved(job.id)}
            >
              <Bookmark size={15} /> {isSaved ? 'Saved' : 'Save Job'}
            </button>
            <a
              className="apply-btn"
              href={job.application_url}
              target="_blank"
              rel="noreferrer"
            >
              Apply on Employer Site <ExternalLink size={14} />
            </a>
          </div>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: 18, borderBottom: '1px solid #edf0f5', padding: '12px 0 0' }}>
          {[
            ['overview', 'Overview'],
            ['requirements', 'Required Skills'],
            ['sponsorship', 'Visa & Relocation'],
            ['fit', "Why You're a Great Fit"]
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key as any)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: tab === key ? '2px solid #087d88' : '2px solid transparent',
                color: tab === key ? '#087d88' : '#687b91',
                fontWeight: 700,
                padding: '6px 4px 10px',
                fontSize: 12,
                cursor: 'pointer'
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="detail-columns" style={{ marginTop: 14 }}>
          {tab === 'overview' && (
            <div>
              <h3>Job Description</h3>
              <p className="description">
                {job.description || 'Full vacancy description is not provided in source feed.'}
              </p>
            </div>
          )}

          {tab === 'requirements' && (
            <div>
              <h3>Required Skills & Technologies</h3>
              <div className="tags" style={{ marginBottom: 18 }}>
                {(job.required_skills || []).map((s) => (
                  <span key={s} style={{ fontSize: 12, padding: '5px 10px' }}>
                    {s}
                  </span>
                ))}
              </div>
              <h3>Role Context</h3>
              <p>
                Targeted AI / ML technical vacancy matching candidate expertise in Python,
                FastAPI, agentic LLM workflows, and model deployment.
              </p>
            </div>
          )}

          {tab === 'sponsorship' && (
            <div>
              <h3>Visa Sponsorship Intelligence</h3>
              <div style={{ background: '#f7fafc', padding: 14, borderRadius: 8, marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Badge status={job.sponsorship_status} />
                  <strong>
                    {job.sponsorship_status === 'confirmed'
                      ? 'Confirmed Visa Sponsorship'
                      : job.sponsorship_status === 'likely'
                      ? 'Likely Sponsorship History'
                      : 'Unverified Vacancy'}
                  </strong>
                </div>
                <p style={{ margin: 0, fontSize: 13, color: '#334155' }}>
                  {job.sponsorship_evidence ||
                    'No vacancy-specific sponsorship statement was extracted from the description.'}
                </p>
              </div>

              {job.relocation_support && (
                <div style={{ background: '#e6faf2', padding: 14, borderRadius: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#00a875', fontWeight: 700 }}>
                    <CheckCircle2 size={16} /> Relocation Assistance Supported
                  </div>
                  <p style={{ margin: '6px 0 0', fontSize: 12, color: '#2d3748' }}>
                    {job.relocation_evidence || 'Relocation allowance or package indicated.'}
                  </p>
                </div>
              )}
            </div>
          )}

          {tab === 'fit' && (
            <div>
              <h3>Candidate Alignment Analysis</h3>
              <div style={{ background: '#eef6fc', padding: 16, borderRadius: 8, marginBottom: 14 }}>
                <h4 style={{ margin: '0 0 6px', color: '#1e3a8a' }}>
                  Talha Aftab &bull; Lead Data Scientist / AI Engineer
                </h4>
                <p style={{ margin: '0 0 10px', fontSize: 12, color: '#3b82f6' }}>
                  Rawalpindi, Pakistan &bull; Immediate Relocation Availability
                </p>
                <p style={{ margin: 0, fontSize: 13, color: '#1e293b' }}>
                  {job.match_explanation || 'Strong technical overlap across core AI engineering requirements.'}
                </p>
              </div>

              <h3>Relevant Demonstrated Projects</h3>
              <ul style={{ fontSize: 12, color: '#475569', lineHeight: 1.7, paddingLeft: 18 }}>
                <li>Autonomous AI Project Management / TPM Agent (LangChain, LangGraph, Multi-Agent)</li>
                <li>Global AI JobPilot Intelligence Platform (FastAPI, Supabase, Public ATS Collectors)</li>
                <li>Production Machine Learning model architectures and REST API integrations</li>
              </ul>
            </div>
          )}

          <aside>
            <h3>Quick Details</h3>
            <div style={{ fontSize: 12, display: 'grid', gap: 10, color: '#475569' }}>
              <div>
                <strong>Posted Date:</strong>{' '}
                {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : 'Recently'}
              </div>
              {job.salary_text && (
                <div>
                  <strong>Salary:</strong> {job.salary_text}
                </div>
              )}
              <div>
                <strong>Source:</strong> {job.source_name || 'Public ATS'}
              </div>
              <div>
                <strong>Canonical ID:</strong> {job.external_id}
              </div>
            </div>

            <div style={{ marginTop: 24 }}>
              <a
                className="apply-btn"
                href={job.application_url}
                target="_blank"
                rel="noreferrer"
                style={{ width: '100%', textAlign: 'center' }}
              >
                Apply on Employer Site &rarr;
              </a>
            </div>
          </aside>
        </div>
      </section>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 4: Sponsorship Tracker
// -------------------------------------------------------------
function SponsorshipScreen({
  jobs,
  saved,
  toggleSaved,
  navigate
}: {
  jobs: Job[];
  saved: string[];
  toggleSaved: (id: string) => void;
  navigate: (s: string) => void;
}) {
  const [filter, setFilter] = useState<'confirmed' | 'likely' | 'unverified' | 'unavailable' | 'all'>('confirmed');

  const counts = {
    confirmed: jobs.filter((j) => j.sponsorship_status === 'confirmed').length,
    likely: jobs.filter((j) => j.sponsorship_status === 'likely').length,
    unverified: jobs.filter((j) => j.sponsorship_status === 'unverified').length,
    unavailable: jobs.filter((j) => j.sponsorship_status === 'unavailable').length
  };

  const list = jobs.filter((j) => (filter === 'all' ? true : j.sponsorship_status === filter));

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">VISA SPONSORSHIP INTELLIGENCE</span>
          <h1>Sponsorship Tracker</h1>
          <p>Evidence-based categorization of worldwide work permits and relocation packages.</p>
        </div>
      </div>

      <div className="stats four">
        <div
          className={`stat card ${filter === 'confirmed' ? 'active-filter' : ''}`}
          style={{ cursor: 'pointer' }}
          onClick={() => setFilter('confirmed')}
        >
          <div className="stat-head">
            <span className="stat-icon green">
              <ShieldCheck size={16} />
            </span>
            <span className="trend">Filtered</span>
          </div>
          <strong>{counts.confirmed}</strong>
          <span className="muted">Confirmed Sponsorship</span>
        </div>

        <div
          className={`stat card ${filter === 'likely' ? 'active-filter' : ''}`}
          style={{ cursor: 'pointer' }}
          onClick={() => setFilter('likely')}
        >
          <div className="stat-head">
            <span className="stat-icon blue">
              <Activity size={16} />
            </span>
            <span className="trend">Filtered</span>
          </div>
          <strong>{counts.likely}</strong>
          <span className="muted">Likely Sponsorship</span>
        </div>

        <div
          className={`stat card ${filter === 'unverified' ? 'active-filter' : ''}`}
          style={{ cursor: 'pointer' }}
          onClick={() => setFilter('unverified')}
        >
          <div className="stat-head">
            <span className="stat-icon purple">
              <Globe2 size={16} />
            </span>
            <span className="trend">Filtered</span>
          </div>
          <strong>{counts.unverified}</strong>
          <span className="muted">Unverified</span>
        </div>

        <div
          className={`stat card ${filter === 'unavailable' ? 'active-filter' : ''}`}
          style={{ cursor: 'pointer' }}
          onClick={() => setFilter('unavailable')}
        >
          <div className="stat-head">
            <span className="stat-icon teal">
              <X size={16} />
            </span>
            <span className="trend">Filtered</span>
          </div>
          <strong>{counts.unavailable}</strong>
          <span className="muted">Unavailable</span>
        </div>
      </div>

      <div className="list-card card" style={{ marginTop: 14 }}>
        {list.length ? (
          list
            .slice(0, 30)
            .map((j) => (
              <JobRow
                key={j.id}
                job={j}
                navigate={navigate}
                saved={saved.includes(j.id)}
                toggleSaved={toggleSaved}
              />
            ))
        ) : (
          <div className="empty-state">
            <ShieldCheck size={24} />
            <h3>No jobs in this category</h3>
            <p>Select another category or collect new vacancies.</p>
          </div>
        )}
      </div>

      <p className="footnote">
        * Confirmed status requires vacancy-specific explicit evidence extracted from employer job
        specifications. Company sponsor registers provide supporting context but are not definitive
        proof for an individual vacancy.
      </p>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 5: Countries
// -------------------------------------------------------------
function CountriesScreen({
  jobs,
  navigate
}: {
  jobs: Job[];
  navigate: (s: string) => void;
}) {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/analytics/countries`)
      .then((r) => (r.ok ? r.json() : []))
      .then((items) => {
        setData(items);
      })
      .catch(() => {});
  }, [jobs]);

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">GLOBAL DESTINATION INTELLIGENCE</span>
          <h1>Opportunities by Country</h1>
          <p>
            Explore international employment hubs, sponsorship density, and candidate match scores.
          </p>
        </div>
      </div>

      <div className="country-grid">
        {data.length ? (
          data.map((c) => (
            <div
              className="card country-card"
              key={c.country}
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(`/jobs?country=${encodeURIComponent(c.country)}`)}
            >
              <Globe2 size={24} />
              <h2>{c.country}</h2>
              <b>{c.jobs} Opportunities</b>
              <p>{c.confirmed} with confirmed sponsorship</p>
              <span>Average candidate fit: {c.average_match}%</span>
            </div>
          ))
        ) : (
          <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
            <Globe2 size={24} />
            <h3>No country data available</h3>
            <p>Run a collection to populate country analytics.</p>
          </div>
        )}
      </div>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 6: Applications Tracker
// -------------------------------------------------------------
function ApplicationsScreen({
  jobs,
  flash,
  navigate
}: {
  jobs: Job[];
  flash: (s: string) => void;
  navigate: (s: string) => void;
}) {
  const [apps, setApps] = useState<any[]>([]);
  const [tab, setTab] = useState('all');

  const loadApps = () => {
    fetch(`${API_BASE}/api/applications`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((res) => setApps(res.items || []))
      .catch(() => {});
  };

  useEffect(() => {
    loadApps();
  }, []);

  const updateStatus = async (appId: string, newStatus: string) => {
    try {
      await fetch(`${API_BASE}/api/applications/${appId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      flash(`Application updated to: ${newStatus}`);
      loadApps();
    } catch {
      flash('Failed to update application status.');
    }
  };

  const addQuickJob = async (job: Job) => {
    try {
      await fetch(`${API_BASE}/api/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: job.id, status: 'saved' })
      });
      flash(`Saved ${job.title} to Applications.`);
      loadApps();
    } catch {
      flash('Failed to save application.');
    }
  };

  const filtered = apps.filter((a) => (tab === 'all' ? true : a.status === tab));

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">APPLICATION PIPELINE</span>
          <h1>Tracked Applications</h1>
          <p>Manage your saved opportunities, submissions, interviews, and offers.</p>
        </div>
      </div>

      <div className="toolbar card">
        <select value={tab} onChange={(e) => setTab(e.target.value)}>
          <option value="all">All Stages ({apps.length})</option>
          <option value="saved">Saved ({apps.filter((a) => a.status === 'saved').length})</option>
          <option value="applied">Applied ({apps.filter((a) => a.status === 'applied').length})</option>
          <option value="interview">Interview ({apps.filter((a) => a.status === 'interview').length})</option>
          <option value="offer">Offer ({apps.filter((a) => a.status === 'offer').length})</option>
          <option value="rejected">Rejected ({apps.filter((a) => a.status === 'rejected').length})</option>
        </select>
        <span className="muted">{filtered.length} tracked records</span>
      </div>

      <section className="list-card card">
        {filtered.length ? (
          filtered.map((a) => {
            const j = a.jobs || {};
            return (
              <article className="app-row" key={a.id}>
                <div>
                  <button
                    className="job-title"
                    onClick={() => navigate(`/job/${a.job_id}`)}
                    style={{ fontSize: 13, textAlign: 'left' }}
                  >
                    {j.title || 'Untitled Role'}
                  </button>
                  <span style={{ fontSize: 11, color: '#64748b' }}>
                    {j.company || 'Unknown Company'} &bull; {j.country || 'International'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Badge status={j.sponsorship_status} />
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#00a875' }}>
                    {j.match_score ? `${j.match_score}% Match` : ''}
                  </span>
                </div>
                <select
                  value={a.status}
                  onChange={(e) => updateStatus(a.id, e.target.value)}
                >
                  <option value="saved">Saved</option>
                  <option value="applied">Applied</option>
                  <option value="interview">Interview</option>
                  <option value="offer">Offer</option>
                  <option value="rejected">Rejected</option>
                </select>
              </article>
            );
          })
        ) : (
          <div className="empty-state">
            <ClipboardList size={26} />
            <h3>No applications in this stage</h3>
            <p>Save roles from the jobs feed or quick-add from top matches below:</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              {jobs.slice(0, 4).map((j) => (
                <button
                  className="suggest-job"
                  key={j.id}
                  onClick={() => addQuickJob(j)}
                >
                  <Plus size={13} /> {j.title} &bull; {j.company}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 7: Sources Management
// -------------------------------------------------------------
function SourcesScreen({
  onRefresh,
  running,
  flash
}: {
  onRefresh: () => void;
  running: boolean;
  flash: (s: string) => void;
}) {
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/sources`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((res) => setSources(res.items || []))
      .catch(() => {});
  }, []);

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">COMPLIANT DATA SOURCES</span>
          <h1>Configured Employer Boards</h1>
          <p>
            Jobs are collected exclusively through official public ATS APIs (Greenhouse, Lever, Ashby).
          </p>
        </div>
        <button className="primary" onClick={onRefresh} disabled={running}>
          <RefreshCw className={running ? 'spin' : ''} size={15} />
          {running ? 'Collecting…' : 'Sync All Sources'}
        </button>
      </div>

      <div className="source-note">
        <ShieldCheck size={18} />
        Zero unauthorized scraping. Only explicitly configured employer board feeds are queried.
      </div>

      <div className="source-grid">
        {sources.length ? (
          sources.map((s) => (
            <div className="card source-card" key={s.board_identifier}>
              <Database size={22} />
              <div>
                <h3>{s.name}</h3>
                <p>
                  {s.type.toUpperCase()} &bull; {s.jobs_collected} jobs indexed
                </p>
              </div>
              <span className="connected">Active</span>
            </div>
          ))
        ) : (
          <div className="card source-empty">
            <Database size={24} />
            <h3>No employer boards configured</h3>
            <p>
              Add Greenhouse, Lever, or Ashby board slugs to <code>EMPLOYER_BOARDS</code> in{' '}
              <code>.env</code>.
            </p>
          </div>
        )}
      </div>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 8: Preferences
// -------------------------------------------------------------
function PreferencesScreen({ flash }: { flash: (s: string) => void }) {
  const [titles, setTitles] = useState('');
  const [skills, setSkills] = useState('');
  const [minScore, setMinScore] = useState(70);
  const [limit, setLimit] = useState(30);
  const [sponsorshipPriority, setSponsorshipPriority] = useState(true);
  const [relocation, setRelocation] = useState(true);
  const [remote, setRemote] = useState(true);
  const [countries, setCountries] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/preferences`)
      .then((r) => (r.ok ? r.json() : null))
      .then((p) => {
        if (p) {
          setTitles((p.target_titles || []).join(', '));
          setSkills((p.skills || []).join(', '));
          setMinScore(p.minimum_match_score ?? 70);
          setLimit(p.daily_notification_limit ?? 30);
          setSponsorshipPriority(Boolean(p.sponsorship_priority));
          setRelocation(Boolean(p.relocation_preference));
          setRemote(Boolean(p.remote_preference));
          setCountries(p.target_countries || []);
        }
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    const payload = {
      target_titles: titles.split(',').map((s) => s.trim()).filter(Boolean),
      skills: skills.split(',').map((s) => s.trim()).filter(Boolean),
      target_countries: countries,
      minimum_match_score: minScore,
      sponsorship_priority: sponsorshipPriority,
      relocation_preference: relocation,
      remote_preference: remote,
      daily_notification_limit: limit
    };

    try {
      const res = await fetch(`${API_BASE}/api/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        flash('Preferences saved successfully and persisted.');
      } else {
        flash('Failed to save preferences.');
      }
    } catch {
      flash('Could not reach preferences API.');
    }
  };

  const toggleCountry = (c: string) => {
    setCountries((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  };

  const allCountries = [
    'United Kingdom',
    'Germany',
    'Netherlands',
    'Ireland',
    'United States',
    'Canada',
    'Australia',
    'Singapore',
    'Japan',
    'United Arab Emirates',
    'Saudi Arabia',
    'New Zealand'
  ];

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">SEARCH CRITERIA</span>
          <h1>Job Search Preferences</h1>
          <p>Customize target engineering roles, technical skills, and notification settings.</p>
        </div>
      </div>

      <div className="settings-grid">
        <section className="card form-card">
          <h2>Job Titles and Skills</h2>
          <label>
            Target Job Titles (comma separated)
            <textarea
              value={titles}
              onChange={(e) => setTitles(e.target.value)}
              rows={3}
            />
          </label>
          <label>
            Technical Expertise & Stack
            <textarea
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              rows={3}
            />
          </label>

          <h2>Matching Parameters</h2>
          <label>
            Minimum Match Score: <b>{minScore}%</b>
            <input
              type="range"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
            />
          </label>

          <label className="checkline">
            <input
              type="checkbox"
              checked={sponsorshipPriority}
              onChange={(e) => setSponsorshipPriority(e.target.checked)}
            />
            Prioritize vacancies offering visa sponsorship
          </label>

          <label className="checkline">
            <input
              type="checkbox"
              checked={relocation}
              onChange={(e) => setRelocation(e.target.checked)}
            />
            Include relocation support opportunities
          </label>

          <label className="checkline">
            <input
              type="checkbox"
              checked={remote}
              onChange={(e) => setRemote(e.target.checked)}
            />
            Include international remote roles
          </label>

          <label>
            Daily Report Notification Limit (Max 30)
            <input
              type="number"
              min={1}
              max={30}
              value={limit}
              onChange={(e) => setLimit(Math.max(1, Math.min(30, Number(e.target.value))))}
            />
          </label>

          <button className="primary" onClick={handleSave} style={{ marginTop: 16 }}>
            Save Preferences <Check size={16} />
          </button>
        </section>

        <section className="card form-card">
          <h2>Target Regions & Countries</h2>
          <div className="check-grid">
            {allCountries.map((c) => (
              <label className="checkline" key={c}>
                <input
                  type="checkbox"
                  checked={countries.includes(c)}
                  onChange={() => toggleCountry(c)}
                />
                {c}
              </label>
            ))}
          </div>
          <p className="muted" style={{ marginTop: 18 }}>
            Selected destinations are prioritized when scoring location compatibility for
            international relocation from Pakistan.
          </p>
        </section>
      </div>
    </>
  );
}

// -------------------------------------------------------------
// SCREEN 9: Settings
// -------------------------------------------------------------
function SettingsScreen({ flash }: { flash: (s: string) => void }) {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setHealth)
      .catch(() => {});
  }, []);

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">SYSTEM & ACCOUNT CONFIGURATION</span>
          <h1>Settings</h1>
          <p>Candidate profile, AI provider status, and infrastructure health.</p>
        </div>
      </div>

      <div className="settings-grid">
        <section className="card form-card">
          <h2>Candidate Profile</h2>
          <label>
            Full Name
            <input defaultValue="Talha Aftab" readOnly />
          </label>
          <label>
            Current Position
            <input defaultValue="Lead Data Scientist / AI Engineer" readOnly />
          </label>
          <label>
            Location
            <input defaultValue="Rawalpindi, Pakistan" readOnly />
          </label>
          <label>
            Online Portfolio
            <input defaultValue="https://talha-portfolio-ten.vercel.app" readOnly />
          </label>
          <label>
            Autonomous TPM Agent
            <input defaultValue="https://apex-tpm-agent.vercel.app" readOnly />
          </label>

          <h2>AI Matching Engine</h2>
          <p className="muted">
            The core matching & sponsorship engine runs locally via heuristic rules with zero cost.
          </p>
          <div className="provider">
            <span>Local Rule-Based Scorer</span>
            <b style={{ color: '#00a875' }}>Active</b>
          </div>
          <div className="provider">
            <span>OpenAI Integration</span>
            <b>{health?.ai_engine?.includes('OpenAI') ? 'Configured' : 'Optional (Free fallback active)'}</b>
          </div>
          <div className="provider">
            <span>Anthropic Claude</span>
            <b>Optional</b>
          </div>
          <div className="provider">
            <span>Google Gemini</span>
            <b>Optional</b>
          </div>
        </section>

        <section className="card form-card">
          <h2>System Health & Architecture</h2>
          <div className="health-row">
            <span>Backend Status</span>
            <b style={{ color: health?.status === 'ok' ? '#00a875' : '#ef4444' }}>
              {health?.status === 'ok' ? 'Online (FastAPI)' : 'Connecting…'}
            </b>
          </div>
          <div className="health-row">
            <span>Indexed Jobs in Database</span>
            <b>{health?.total_jobs ?? '—'} live jobs</b>
          </div>
          <div className="health-row">
            <span>Configured Sources</span>
            <b>{health?.sources_configured ?? '—'} employer boards</b>
          </div>
          <div className="health-row">
            <span>Supabase Persistence</span>
            <b>{health?.database_configured ? 'Configured' : 'Local SQLite Fallback Active'}</b>
          </div>
          <div className="health-row">
            <span>Automated Schedule</span>
            <b>03:00 UTC (GitHub Actions)</b>
          </div>

          <p className="footnote" style={{ marginTop: 22 }}>
            Row Level Security (RLS) is enabled in Supabase migrations. Service role keys remain
            securely on the backend and are never sent to the browser client.
          </p>
        </section>
      </div>
    </>
  );
}

export default App;
