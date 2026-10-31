import os

# 1. Create all necessary directories
dirs_to_create = [
    'app', 'app/models', 'app/routes', 'app/services', 
    'app/permissions', 'app/validators', 'app/templates',
    'app/static/css', 'app/static/js', 'app/static/fonts', 
    'app/static/images', 'app/static/vendor',
    'migrations', 'tests/unit', 'tests/integration', 
    'tests/security', 'tests/e2e', 'scripts', 'instance', 
    'uploads', 'logs'
]

for directory in dirs_to_create:
    os.makedirs(directory, exist_ok=True)

# 2. Create __init__.py files to make them valid Python packages
packages = [
    'app', 'app/models', 'app/routes', 'app/services', 
    'app/permissions', 'app/validators'
]

for package in packages:
    init_path = os.path.join(package, '__init__.py')
    if not os.path.exists(init_path):
        with open(init_path, 'w') as f:
            f.write('')
        print(f"Created {init_path}")
    else:
        print(f"{init_path} already exists.")

print("\n✅ Project structure fixed successfully!")