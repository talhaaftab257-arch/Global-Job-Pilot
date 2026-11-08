export type Job = {
  id: string;
  external_id?: string | null;
  canonical_url?: string;
  title: string;
  company: string;
  location: string | null;
  country: string | null;
  description: string | null;
  application_url: string;
  posted_at: string | null;
  salary_text: string | null;
  required_skills: string[];
  sponsorship_status: 'confirmed' | 'likely' | 'unverified' | 'unavailable';
  sponsorship_evidence: string | null;
  relocation_support: boolean | null;
  relocation_evidence?: string | null;
  match_score: number | null;
  technical_score?: number | null;
  role_score?: number | null;
  ai_relevance_score?: number | null;
  experience_score?: number | null;
  sponsorship_score?: number | null;
  location_score?: number | null;
  recency_score?: number | null;
  match_explanation: string | null;
  source_name?: string;
  employment_type?: string | null;
  remote_type?: string | null;
};

export type JobSource = {
  name: string;
  type: string;
  slug: string;
  board_identifier: string;
  source_url?: string;
  active: boolean;
  jobs_collected?: number;
};

export type ApplicationRecord = {
  id: string;
  job_id: string;
  status: 'saved' | 'applied' | 'interview' | 'offer' | 'rejected' | 'follow_up';
  applied_at?: string | null;
  notes?: string | null;
  created_at: string;
  jobs?: Partial<Job>;
};
