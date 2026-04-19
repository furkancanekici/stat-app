import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/shared/Navbar";
import UploadPage from "./pages/UploadPage";
import ViewerPage from "./pages/ViewerPage";
import ReportPage from "./pages/ReportPage";
import PreliminaryPage from "./pages/PreliminaryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/viewer" element={<ViewerPage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/preliminary" element={<PreliminaryPage />} />
      </Routes>
    </BrowserRouter>
  );
}