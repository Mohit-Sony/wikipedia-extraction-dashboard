module.exports = {
  apps: [
        {
      name: 'wikipedia-backend',

      script: 'main.py',
      cwd: './backend',

      interpreter: './venv/bin/python',

      exec_mode: 'fork',
      instances: 1,
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