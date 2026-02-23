from flask import Blueprint

# We will register all blueprints here
def register_routes(app):
    from .watchlist import watchlist_bp
    from .company import company_bp
    from .portfolio import portfolio_bp
    from .agent import agent_bp
    from .backtest import backtest_bp
    from .algorithms import algorithms_bp
    from .articles import articles_bp
    
    app.register_blueprint(watchlist_bp, url_prefix='/api/watchlist')
    app.register_blueprint(company_bp, url_prefix='/api/company')
    app.register_blueprint(portfolio_bp, url_prefix='/api/portfolio')
    app.register_blueprint(agent_bp, url_prefix='/api/agent')
    app.register_blueprint(backtest_bp, url_prefix='/api/backtest')
    app.register_blueprint(algorithms_bp, url_prefix='/api')
    app.register_blueprint(articles_bp, url_prefix='/api')
