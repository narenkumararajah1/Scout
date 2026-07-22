export interface Notification {
  id: string;
  company_id: string;
  type: string;
  title: string;
  summary: string | null;
  recommended_action: string | null;
  is_read: boolean;
  created_at: string;
}
