module.exports = {
  apps: [
    {
      name: 'wikipedia-backend',

      // Use uvicorn from venv directly
      script: './venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000',

      cwd: './backend',

      instances: 1,
      exec_mode: 'fork',   // IMPORTANT for Python apps
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',

      env: {
        PYTHONUNBUFFERED: '1'
      },

      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true
    },

    {
      name: 'wikipedia-frontend',
      script: 'npx',
      args: 'serve -s dist -l 3000',
      cwd: './frontend',
      interpreter: 'none',

      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',

      env: {
        NODE_ENV: 'production'
      },

      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true
    }
  ]
};