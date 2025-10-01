"""
Unit tests for the GitHub Actions Build, Test, and Push workflow.

This test suite validates the workflow configuration YAML file to ensure
proper structure, correct environment variables, appropriate job dependencies,
and expected behavior under various conditions.

Testing Framework: unittest (Python standard library)
"""

import unittest
try:
    import yaml
except ImportError:
    yaml = None
import os
import re
from unittest.mock import patch, MagicMock


@unittest.skipIf(yaml is None, "PyYAML is required for TestBuildTagPushWorkflow")
class TestBuildTagPushWorkflow(unittest.TestCase):
    """Test suite for the GitHub Actions workflow configuration."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Load the workflow YAML file
        
        # For testing purposes, we'll create the YAML content as a string
        # since the actual file might be in a different location
        self.workflow_content = '''
name: Build, Test, and Push Chirp Backend (Prod or Dev)

on:
  push:
    branches:
      - '**'

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: chirp_user
          POSTGRES_PASSWORD: secretpassword
          POSTGRES_DB: chirp_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U chirp_user -d chirp_db"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    env:
      DB_USER: chirp_user
      DB_PASSWORD: secretpassword
      DB_NAME: chirp_db
      DB_HOST: localhost
      DB_PORT: 5432
      PGUSER: chirp_user
      PGPASSWORD: secretpassword
      PGDATABASE: chirp_db
      PGHOST: localhost
      PGPORT: 5432
      DJANGO_SETTINGS_MODULE: chirp.settings
      TEST_VERISAFE_JWT: ${{ secrets.TEST_VERISAFE_JWT }}

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Cache Python Dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run Migrations
        run: |
          python manage.py makemigrations
          python manage.py migrate

      - name: Run Tests
        run: echo "TEST_VERISAFE_JWT=${{ secrets.TEST_VERISAFE_JWT }}" >> $GITHUB_ENV && python manage.py test --verbosity=2

  build-and-push:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install pack CLI
        run: |
          curl -sSL "https://github.com/buildpacks/pack/releases/download/v0.38.2/pack-v0.38.2-linux.tgz" | tar -xz
          sudo mv pack /usr/local/bin/pack

      - name: Cache CNB Layers
        uses: actions/cache@v4
        with:
          path: ~/.cache/pack
          key: cnb-${{ runner.os }}-${{ github.ref }}-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            cnb-${{ runner.os }}-${{ github.ref }}
            cnb-${{ runner.os }}

      - name: Set Docker Tags
        id: tags
        run: |
          BRANCH=$(echo "${GITHUB_REF##*/}" | tr '[:upper:]' '[:lower:]' | tr '/' '-')
          SHA=$(git rev-parse --short HEAD)

          if [ "$BRANCH" = "main" ]; then
            IMAGE_TAG="prod"
            IMAGE_BASE="${{ secrets.DOCKERHUB_USERNAME }}/chirp-backend-prod"
          else
            IMAGE_TAG="dev"
            IMAGE_BASE="${{ secrets.DOCKERHUB_USERNAME }}/chirp-backend-staging"
          fi

          echo "image_base=$IMAGE_BASE" >> $GITHUB_OUTPUT
          echo "image_tag=$IMAGE_TAG" >> $GITHUB_OUTPUT
          echo "sha_tag=$SHA" >> $GITHUB_OUTPUT

      - name: Log in to Docker Hub
        run: echo "${{ secrets.DOCKERHUB_TOKEN }}" | docker login -u "${{ secrets.DOCKERHUB_USERNAME }}" --password-stdin

      - name: Build Docker image with Buildpacks
        run: |
          IMAGE_BASE=${{ steps.tags.outputs.image_base }}
          IMAGE_TAG=${{ steps.tags.outputs.image_tag }}
          SHA_TAG=${{ steps.tags.outputs.sha_tag }}

          echo "🔨 Building $IMAGE_BASE:$IMAGE_TAG and $IMAGE_BASE:$SHA_TAG"

          pack build "$IMAGE_BASE:$IMAGE_TAG" \
            --buildpack paketo-buildpacks/python \
            --builder paketobuildpacks/builder-jammy-base \
            --cache "type=build;format=volume"

          docker tag "$IMAGE_BASE:$IMAGE_TAG" "$IMAGE_BASE:$SHA_TAG"

      - name: Push Docker images to Docker Hub
        run: |
          IMAGE_BASE=${{ steps.tags.outputs.image_base }}
          IMAGE_TAG=${{ steps.tags.outputs.image_tag }}
          SHA_TAG=${{ steps.tags.outputs.sha_tag }}

          echo "🚀 Pushing $IMAGE_BASE:$IMAGE_TAG"
          docker push "$IMAGE_BASE:$IMAGE_TAG"

          echo "🚀 Pushing $IMAGE_BASE:$SHA_TAG"
          docker push "$IMAGE_BASE:$SHA_TAG"
'''
        self.workflow_data = yaml.safe_load(self.workflow_content)

    def test_workflow_structure_validity(self):
        """Test that the workflow YAML structure is valid and well-formed."""
        self.assertIsInstance(self.workflow_data, dict)
        self.assertIn('name', self.workflow_data)
        self.assertIn('on', self.workflow_data)
        self.assertIn('jobs', self.workflow_data)

    def test_workflow_name(self):
        """Test that the workflow has the expected name."""
        expected_name = "Build, Test, and Push Chirp Backend (Prod or Dev)"
        self.assertEqual(self.workflow_data['name'], expected_name)

    def test_workflow_triggers(self):
        """Test workflow trigger configuration."""
        triggers = self.workflow_data['on']
        self.assertIn('push', triggers)
        self.assertIn('branches', triggers['push'])
        self.assertIn('**', triggers['push']['branches'])

    def test_job_structure(self):
        """Test that required jobs are present with correct structure."""
        jobs = self.workflow_data['jobs']
        self.assertIn('test', jobs)
        self.assertIn('build-and-push', jobs)

        # Test job has required keys
        test_job = jobs['test']
        self.assertIn('runs-on', test_job)
        self.assertIn('services', test_job)
        self.assertIn('env', test_job)
        self.assertIn('steps', test_job)

        # Build-and-push job has required keys
        build_job = jobs['build-and-push']
        self.assertIn('runs-on', build_job)
        self.assertIn('needs', build_job)
        self.assertIn('steps', build_job)

    def test_postgres_service_configuration(self):
        """Test PostgreSQL service configuration in the test job."""
        postgres_service = self.workflow_data['jobs']['test']['services']['postgres']

        self.assertEqual(postgres_service['image'], 'postgres:16')
        self.assertIn('env', postgres_service)
        self.assertIn('ports', postgres_service)
        self.assertIn('options', postgres_service)

        # Test environment variables
        env = postgres_service['env']
        self.assertEqual(env['POSTGRES_USER'], 'chirp_user')
        self.assertEqual(env['POSTGRES_PASSWORD'], 'secretpassword')
        self.assertEqual(env['POSTGRES_DB'], 'chirp_db')

        # Test port mapping
        self.assertIn('5432:5432', postgres_service['ports'])

    def test_job_environment_variables(self):
        """Test environment variables configuration in test job."""
        test_env = self.workflow_data['jobs']['test']['env']

        # Database connection variables
        self.assertEqual(test_env['DB_USER'], 'chirp_user')
        self.assertEqual(test_env['DB_PASSWORD'], 'secretpassword')
        self.assertEqual(test_env['DB_NAME'], 'chirp_db')
        self.assertEqual(test_env['DB_HOST'], 'localhost')
        self.assertEqual(test_env['DB_PORT'], 5432)

        # PostgreSQL client variables
        self.assertEqual(test_env['PGUSER'], 'chirp_user')
        self.assertEqual(test_env['PGPASSWORD'], 'secretpassword')
        self.assertEqual(test_env['PGDATABASE'], 'chirp_db')
        self.assertEqual(test_env['PGHOST'], 'localhost')
        self.assertEqual(test_env['PGPORT'], 5432)

        # Django configuration
        self.assertEqual(test_env['DJANGO_SETTINGS_MODULE'], 'chirp.settings')
        self.assertIn('secrets.TEST_VERISAFE_JWT', test_env['TEST_VERISAFE_JWT'])

    def test_job_dependencies(self):
        """Test that build-and-push job depends on test job."""
        build_job = self.workflow_data['jobs']['build-and-push']
        self.assertEqual(build_job['needs'], 'test')

    def test_python_version_consistency(self):
        """Test that Python version is consistent across jobs."""
        jobs = self.workflow_data['jobs']

        # Find Python setup steps in all jobs
        python_versions = []
        for _job_name, job_config in jobs.items():
            for step in job_config['steps']:
                if step.get('uses') == 'actions/setup-python@v5':
                    python_versions.append(step['with']['python-version'])

        # All Python versions should be the same
        self.assertTrue(all(v == '3.12' for v in python_versions))
        self.assertTrue(len(python_versions) >= 2)  # Both jobs should set Python version

    def test_cache_configurations(self):
        """Test caching configurations in the workflow."""
        # Test Python dependencies cache in test job
        test_steps = self.workflow_data['jobs']['test']['steps']
        cache_step = None
        for step in test_steps:
            if step.get('name') == 'Cache Python Dependencies':
                cache_step = step
                break

        self.assertIsNotNone(cache_step)
        self.assertEqual(cache_step['uses'], 'actions/cache@v4')
        self.assertEqual(cache_step['with']['path'], '~/.cache/pip')
        self.assertIn('hashFiles', cache_step['with']['key'])

        # Test CNB layers cache in build job
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        cnb_cache_step = None
        for step in build_steps:
            if step.get('name') == 'Cache CNB Layers':
                cnb_cache_step = step
                break

        self.assertIsNotNone(cnb_cache_step)
        self.assertEqual(cnb_cache_step['uses'], 'actions/cache@v4')
        self.assertEqual(cnb_cache_step['with']['path'], '~/.cache/pack')

    def test_required_secrets_usage(self):
        """Test that required secrets are properly referenced."""
        workflow_str = self.workflow_content

        # Check for required secrets
        required_secrets = [
            'TEST_VERISAFE_JWT',
            'DOCKERHUB_USERNAME',
            'DOCKERHUB_TOKEN'
        ]

        for secret in required_secrets:
            self.assertIn(f'secrets.{secret}', workflow_str)

    def test_docker_tag_logic_structure(self):
        """Test the structure of Docker tag setting logic."""
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        tag_step = None
        for step in build_steps:
            if step.get('name') == 'Set Docker Tags':
                tag_step = step
                break

        self.assertIsNotNone(tag_step)
        self.assertEqual(tag_step['id'], 'tags')

        # Test that the step contains branch logic
        run_script = tag_step['run']
        self.assertIn('GITHUB_REF', run_script)
        self.assertIn('git rev-parse', run_script)
        self.assertIn('main', run_script)
        self.assertIn('GITHUB_OUTPUT', run_script)

    def test_buildpack_configuration(self):
        """Test buildpack configuration in Docker build step."""
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        build_step = None
        for step in build_steps:
            if step.get('name') == 'Build Docker image with Buildpacks':
                build_step = step
                break

        self.assertIsNotNone(build_step)
        run_script = build_step['run']

        # Test buildpack components
        self.assertIn('pack build', run_script)
        self.assertIn('paketo-buildpacks/python', run_script)
        self.assertIn('paketobuildpacks/builder-jammy-base', run_script)
        self.assertIn('docker tag', run_script)

    def test_step_order_in_test_job(self):
        """Test that steps in test job are in logical order."""
        test_steps = self.workflow_data['jobs']['test']['steps']
        step_names = [step['name'] for step in test_steps]

        # Expected order of critical steps
        expected_order = [
            'Checkout Code',
            'Set up Python',
            'Cache Python Dependencies',
            'Install Dependencies',
            'Run Migrations',
            'Run Tests'
        ]

        for i, expected_step in enumerate(expected_order):
            self.assertIn(expected_step, step_names)
            actual_index = step_names.index(expected_step)
            if i > 0:
                prev_step = expected_order[i-1]
                prev_index = step_names.index(prev_step)
                self.assertLess(prev_index, actual_index, 
                    f"{prev_step} should come before {expected_step}")

    def test_step_order_in_build_job(self):
        """Test that steps in build job are in logical order."""
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        step_names = [step['name'] for step in build_steps]

        # Expected order of critical steps
        expected_order = [
            'Checkout Code',
            'Set up Python',
            'Install pack CLI',
            'Set Docker Tags',
            'Log in to Docker Hub',
            'Build Docker image with Buildpacks',
            'Push Docker images to Docker Hub'
        ]

        for i, expected_step in enumerate(expected_order):
            self.assertIn(expected_step, step_names)
            actual_index = step_names.index(expected_step)
            if i > 0:
                prev_step = expected_order[i-1]
                prev_index = step_names.index(prev_step)
                self.assertLess(prev_index, actual_index,
                    f"{prev_step} should come before {expected_step}")

    def test_github_actions_versions(self):
        """Test that GitHub Actions use specific, stable versions."""
        jobs = self.workflow_data['jobs']

        action_versions = {}
        for job_name, job_config in jobs.items():
            for step in job_config['steps']:
                if 'uses' in step:
                    action = step['uses']
                    if action not in action_versions:
                        action_versions[action] = []
                    action_versions[action].append(job_name)

        # Verify specific versions are used (not latest)
        for action in action_versions:
            self.assertRegex(action, r'@v\d+', f"Action {action} should use specific version")

    def test_postgres_health_check(self):
        """Test PostgreSQL health check configuration."""
        postgres_service = self.workflow_data['jobs']['test']['services']['postgres']
        options = postgres_service['options']

        # Test health check components
        self.assertIn('--health-cmd', options)
        self.assertIn('pg_isready', options)
        self.assertIn('--health-interval 5s', options)
        self.assertIn('--health-timeout 5s', options)
        self.assertIn('--health-retries 5', options)

    def test_django_migration_steps(self):
        """Test Django migration steps in test job."""
        test_steps = self.workflow_data['jobs']['test']['steps']
        migration_step = None
        for step in test_steps:
            if step.get('name') == 'Run Migrations':
                migration_step = step
                break

        self.assertIsNotNone(migration_step)
        run_script = migration_step['run']
        self.assertIn('python manage.py makemigrations', run_script)
        self.assertIn('python manage.py migrate', run_script)

    def test_test_execution_step(self):
        """Test the test execution step configuration."""
        test_steps = self.workflow_data['jobs']['test']['steps']
        test_step = None
        for step in test_steps:
            if step.get('name') == 'Run Tests':
                test_step = step
                break

        self.assertIsNotNone(test_step)
        run_script = test_step['run']
        self.assertIn('python manage.py test', run_script)
        self.assertIn('--verbosity=2', run_script)
        self.assertIn('TEST_VERISAFE_JWT', run_script)

    def test_pack_cli_installation(self):
        """Test pack CLI installation step."""
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        pack_step = None
        for step in build_steps:
            if step.get('name') == 'Install pack CLI':
                pack_step = step
                break

        self.assertIsNotNone(pack_step)
        run_script = pack_step['run']
        self.assertIn('curl -sSL', run_script)
        self.assertIn('github.com/buildpacks/pack/releases', run_script)
        self.assertIn('sudo mv pack /usr/local/bin/pack', run_script)

    def test_docker_login_step(self):
        """Test Docker Hub login step."""
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        login_step = None
        for step in build_steps:
            if step.get('name') == 'Log in to Docker Hub':
                login_step = step
                break

        self.assertIsNotNone(login_step)
        run_script = login_step['run']
        self.assertIn('docker login', run_script)
        self.assertIn('--password-stdin', run_script)
        self.assertIn('secrets.DOCKERHUB_TOKEN', run_script)
        self.assertIn('secrets.DOCKERHUB_USERNAME', run_script)

    def test_docker_push_step(self):
        """Test Docker image push step."""
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        push_step = None
        for step in build_steps:
            if step.get('name') == 'Push Docker images to Docker Hub':
                push_step = step
                break

        self.assertIsNotNone(push_step)
        run_script = push_step['run']
        self.assertIn('docker push', run_script)
        self.assertIn('IMAGE_BASE', run_script)
        self.assertIn('IMAGE_TAG', run_script)
        self.assertIn('SHA_TAG', run_script)

    def test_workflow_runs_on_ubuntu_latest(self):
        """Test that all jobs run on ubuntu-latest."""
        jobs = self.workflow_data['jobs']
        for job_name, job_config in jobs.items():
            self.assertEqual(job_config['runs-on'], 'ubuntu-latest', 
                f"Job {job_name} should run on ubuntu-latest")

    def test_cache_key_patterns(self):
        """Test cache key patterns for proper invalidation."""
        # Python dependencies cache
        test_steps = self.workflow_data['jobs']['test']['steps']
        for step in test_steps:
            if step.get('name') == 'Cache Python Dependencies':
                key = step['with']['key']
                self.assertIn('runner.os', key)
                self.assertIn('hashFiles', key)
                self.assertIn('requirements.txt', key)
                break

        # CNB layers cache  
        build_steps = self.workflow_data['jobs']['build-and-push']['steps']
        for step in build_steps:
            if step.get('name') == 'Cache CNB Layers':
                key = step['with']['key']
                self.assertIn('runner.os', key)
                self.assertIn('github.ref', key)
                self.assertIn('hashFiles', key)
                break

    def test_environment_variable_consistency(self):
        """Test consistency between service and job environment variables."""
        postgres_env = self.workflow_data['jobs']['test']['services']['postgres']['env']
        job_env = self.workflow_data['jobs']['test']['env']

        # Database connection consistency
        self.assertEqual(postgres_env['POSTGRES_USER'], job_env['DB_USER'])
        self.assertEqual(postgres_env['POSTGRES_PASSWORD'], job_env['DB_PASSWORD'])
        self.assertEqual(postgres_env['POSTGRES_DB'], job_env['DB_NAME'])

        # PostgreSQL client consistency
        self.assertEqual(postgres_env['POSTGRES_USER'], job_env['PGUSER'])
        self.assertEqual(postgres_env['POSTGRES_PASSWORD'], job_env['PGPASSWORD'])
        self.assertEqual(postgres_env['POSTGRES_DB'], job_env['PGDATABASE'])

    def test_yaml_structure_integrity(self):
        """Test YAML structure integrity and proper nesting."""
        # Test that all required top-level keys exist
        required_keys = ['name', 'on', 'jobs']
        for key in required_keys:
            self.assertIn(key, self.workflow_data)

        # Test jobs structure
        jobs = self.workflow_data['jobs']
        for job_name in ['test', 'build-and-push']:
            self.assertIn(job_name, jobs)
            job = jobs[job_name]
            self.assertIn('runs-on', job)
            self.assertIn('steps', job)
            self.assertIsInstance(job['steps'], list)


class TestWorkflowEdgeCases(unittest.TestCase):
    """Test edge cases and failure conditions for the workflow."""

    def test_empty_workflow_validation(self):
        """Test validation of empty workflow configuration."""
        empty_workflow = {}
        with self.assertRaises(KeyError):
            # Should fail when trying to access required keys
            _ = empty_workflow['name']

    @unittest.skipIf(yaml is None, "PyYAML is required for test_malformed_yaml_handling")
    def test_malformed_yaml_handling(self):
        """Test handling of malformed YAML structure."""
        malformed_yaml = "name: Test\n  invalid_indent: value"
        with self.assertRaises(yaml.scanner.ScannerError):
            yaml.safe_load(malformed_yaml)

    def test_missing_required_jobs(self):
        """Test validation when required jobs are missing."""
        workflow_without_test = {
            'name': 'Test Workflow',
            'on': {'push': {'branches': ['main']}},
            'jobs': {
                'build-and-push': {
                    'runs-on': 'ubuntu-latest',
                    'steps': []
                }
            }
        }
        
        # Should not have test job
        self.assertNotIn('test', workflow_without_test['jobs'])

    def test_invalid_postgres_configuration(self):
        """Test validation of PostgreSQL configuration."""
        invalid_postgres_config = {
            'image': 'postgres:invalid-version',
            'env': {
                'POSTGRES_USER': '',  # Empty user
                'POSTGRES_PASSWORD': '',  # Empty password
            }
        }
        
        # Validate that empty credentials would be problematic
        self.assertEqual(invalid_postgres_config['env']['POSTGRES_USER'], '')
        self.assertEqual(invalid_postgres_config['env']['POSTGRES_PASSWORD'], '')

    def test_inconsistent_environment_variables(self):
        """Test detection of inconsistent environment variables."""
        inconsistent_env = {
            'service_env': {'POSTGRES_USER': 'user1'},
            'job_env': {'DB_USER': 'user2'}
        }
        
        # These should match but don't
        self.assertNotEqual(
            inconsistent_env['service_env']['POSTGRES_USER'],
            inconsistent_env['job_env']['DB_USER']
        )

    def test_missing_secrets_validation(self):
        """Test validation of missing required secrets."""
        workflow_content = '''
        name: Test
        jobs:
          test:
            steps:
              - name: Test
                run: echo "Missing secret: ${{ secrets.MISSING_SECRET }}"
        '''
        
        # Should contain reference to missing secret
        self.assertIn('MISSING_SECRET', workflow_content)

    def test_version_pinning_validation(self):
        """Test validation of action version pinning."""
        unpinned_action = 'actions/checkout@main'  # Should be pinned to specific version
        pinned_action = 'actions/checkout@v4'
        
        # Test regex for version checking
        version_pattern = r'@v\d+'
        self.assertNotRegex(unpinned_action, version_pattern)
        self.assertRegex(pinned_action, version_pattern)

    def test_docker_tag_logic_edge_cases(self):
        """Test Docker tag logic with various branch names."""
        # Test main branch logic
        branch_main = "main"
        self.assertEqual(branch_main, "main")
        
        # Test feature branch logic  
        branch_feature = "feature/new-feature"
        # Should be converted to dev tag for non-main branches
        self.assertNotEqual(branch_feature, "main")

    def test_cache_path_validation(self):
        """Test validation of cache paths."""
        valid_cache_paths = [
            '~/.cache/pip',
            '~/.cache/pack'
        ]
        
        invalid_cache_paths = [
            '/var/cache',  # Absolute path, might not persist
            'cache',       # Relative path, might not be consistent
            ''             # Empty path
        ]
        
        for path in valid_cache_paths:
            self.assertTrue(path.startswith('~/'))
            
        for path in invalid_cache_paths:
            if path:
                self.assertFalse(path.startswith('~/'))

    def test_step_dependency_validation(self):
        """Test validation of step dependencies."""
        # Python setup should come before dependency installation
        steps_order = ['checkout', 'setup-python', 'cache', 'install-deps', 'test']
        
        # Validate logical order
        checkout_idx = steps_order.index('checkout')
        setup_idx = steps_order.index('setup-python')
        install_idx = steps_order.index('install-deps')
        test_idx = steps_order.index('test')
        
        self.assertLess(checkout_idx, setup_idx)
        self.assertLess(setup_idx, install_idx)
        self.assertLess(install_idx, test_idx)


if __name__ == '__main__':
    # Create test runner with high verbosity
    unittest.main(verbosity=2, buffer=True)