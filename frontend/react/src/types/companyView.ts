// Mirrors backend/schemas/company_view.py's CompanyVisitChangesResponse
// exactly (roadmap Phase 3 - "What Changed Since Last Visit").

export interface CompanyVisitNotification {
  id: string;
  title: string;
  type: string;
  recommended_action: string | null;
}

export interface CompanyVisitChanges {
  first_visit: boolean;
  since: string | null;
  new_notifications: CompanyVisitNotification[];
  new_opportunity_count: number;
  new_report_count: number;
}
