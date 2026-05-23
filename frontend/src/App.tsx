import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuth } from "./store/auth";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { CoursesPage } from "./pages/CoursesPage";
import { CourseDetail } from "./pages/CourseDetail";
import { AttendancePage } from "./pages/AttendancePage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { GroupsPage } from "./pages/GroupsPage";

function App() {
  const { token, fetchMe } = useAuth();

  useEffect(() => {
    if (token) fetchMe();
  }, [token]);

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/courses" element={<CoursesPage />} />
                  <Route path="/courses/:courseId" element={<CourseDetail />} />
                  <Route path="/groups" element={<GroupsPage />} />
                  <Route path="/attendance" element={<AttendancePage />} />
                  <Route path="/analytics" element={<AnalyticsPage />} />
                  <Route path="*" element={<Navigate to="/" />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
