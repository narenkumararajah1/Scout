import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { AdministrationPage } from "./pages/AdministrationPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AskScoutPage } from "./pages/AskScoutPage";
import { CompaniesPage } from "./pages/CompaniesPage";
import { CompanyDetailsPage } from "./pages/CompanyDetailsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { KnowledgeDocumentDetailPage } from "./pages/KnowledgeDocumentDetailPage";
import { KnowledgeLibraryPage } from "./pages/KnowledgeLibraryPage";
import { LoginPage } from "./pages/LoginPage";
import { MeetingBriefDetailPage } from "./pages/MeetingBriefDetailPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { OutreachDraftDetailPage } from "./pages/OutreachDraftDetailPage";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { SalesEnablementPage } from "./pages/SalesEnablementPage";
import { SalesPlaybookDetailPage } from "./pages/SalesPlaybookDetailPage";
import { SettingsPage } from "./pages/SettingsPage";
import { V3ReportDetailPage } from "./pages/V3ReportDetailPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="companies" element={<CompaniesPage />} />
        <Route path="companies/:companyId" element={<CompanyDetailsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="sales-enablement" element={<SalesEnablementPage />} />
        <Route path="ask-scout" element={<AskScoutPage />} />
        <Route path="knowledge" element={<KnowledgeLibraryPage />} />
        <Route path="knowledge/:documentId" element={<KnowledgeDocumentDetailPage />} />
        <Route path="administration" element={<AdministrationPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="reports/:reportId" element={<ReportDetailPage />} />
        <Route path="sales-playbooks/:playbookId" element={<SalesPlaybookDetailPage />} />
        <Route path="meeting-briefs/:briefId" element={<MeetingBriefDetailPage />} />
        <Route path="outreach-drafts/:draftId" element={<OutreachDraftDetailPage />} />
        <Route path="v3-reports/:reportId" element={<V3ReportDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
