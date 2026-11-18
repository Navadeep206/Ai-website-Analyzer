import React, { useState } from 'react'
import { AppLayout } from './components/layout/AppLayout'
import { AnalysisProvider, useAnalysis } from './context/AnalysisContext'
import { Dashboard } from './pages/Dashboard'
import { ResultsPage } from './pages/ResultsPage'

function WorkspaceShell() {
  const [activeView, setActiveView] = useState('dashboard')
  const { result, resetAnalysis } = useAnalysis()

  const handleSelectView = (nextView) => {
    if (nextView === 'dashboard' && activeView === 'results') {
      resetAnalysis()
    }
    setActiveView(nextView)
  }

  const handleStartNewFromResults = () => {
    resetAnalysis()
    setActiveView('dashboard')
  }

  return (
    <AppLayout activeView={activeView} onSelectView={handleSelectView}>
      {activeView === 'results' && result ? (
        <ResultsPage
          data={result}
          onStartNewAnalysis={handleStartNewFromResults}
        />
      ) : (
        <Dashboard
          onSelectView={handleSelectView}
          onAnalysisComplete={() => setActiveView('results')}
        />
      )}
    </AppLayout>
  )
}

export default function App() {
  return (
    <AnalysisProvider>
      <WorkspaceShell />
    </AnalysisProvider>
  )
}
