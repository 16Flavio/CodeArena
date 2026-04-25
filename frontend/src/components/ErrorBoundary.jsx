import { Component } from 'react';
import { withTranslation } from 'react-i18next';
import { AlertCircle } from 'lucide-react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || '' };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('UI crash:', error, info?.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, message: '' });
    window.location.reload();
  };

  render() {
    const { t, children } = this.props;
    if (!this.state.hasError) return children;
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 dark:bg-slate-950">
        <div className="glass-card p-8 max-w-lg w-full text-center">
          <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4 dark:text-amber-400" />
          <h1 className="text-xl font-bold text-slate-900 mb-2 dark:text-white">
            {t('errorBoundary.title')}
          </h1>
          <p className="text-sm text-slate-600 mb-6 dark:text-gray-400">
            {t('errorBoundary.body')}
          </p>
          {this.state.message && (
            <pre className="text-[11px] text-left text-slate-500 bg-gray-100 dark:bg-slate-900/50 dark:text-gray-400 p-3 rounded-lg overflow-auto mb-4 max-h-40">
              {this.state.message}
            </pre>
          )}
          <button type="button" onClick={this.handleReload} className="btn-primary text-sm">
            {t('errorBoundary.reload')}
          </button>
        </div>
      </div>
    );
  }
}

export default withTranslation()(ErrorBoundary);
