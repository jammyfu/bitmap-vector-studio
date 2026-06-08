/// Header component displaying the application title and branding.
function Header() {
  return (
    <header className="app-header">
      <div className="logo">
        <span className="logo-icon">◈</span>
        <h1>Bitmap Vector Studio</h1>
      </div>
      <div className="version">v0.5.0</div>
    </header>
  )
}

export default Header
