import { HashRouter, Routes, Route } from "react-router-dom"
import { Header } from "./components/Header"
import { HomePage } from "./components/HomePage"
import { ConsolePage } from "./components/ConsolePage"
import { ResultsPage } from "./components/ResultsPage"
import { CustomCursor } from "./components/CustomCursor"
import { Preloader } from "./components/Preloader"

function App() {
  return (
    <HashRouter>
      <div className="min-h-screen">
        <Preloader />
        <CustomCursor />
        <Header />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/app" element={<ConsolePage />} />
          <Route path="/results" element={<ResultsPage />} />
        </Routes>
      </div>
    </HashRouter>
  )
}

export default App
