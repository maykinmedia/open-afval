#!groovy

// Use "node {...}" to use any Jenkins server, or "node('master') {...}" to
// only run on the master node.
node {
    // You can hardcode the settings here, or have it dynamically figured out
    // in the build step.
    def djangoSettings = null
    def curDir = pwd()
    def envDir = "${curDir}/env"
    def testResultsFile = "${curDir}/reports/junit.xml"
    def testCoverageFile = "${curDir}/reports/coverage.xml"

    stage ("Build") {
        // Submit to Chucks will
        chuckNorris()

        // Use the clean option that fits best in the project.
        // Clean build when changing target
        if (env.CHANGE_TARGET) {
            // Clean workspace
            // cleanWs()

            // Clean virtual environment
            dir("env") {
                deleteDir()
            }
        }
        // Clean build when the previous build failed.
        // cleanWs cleanWhenNotBuilt: false, cleanWhenSuccess: false, notFailBuild: true

        // Install python from pyproject.toml
        sh 'alias "uv=/home/maykin/.local/bin/uv"'
        sh "uv python install"

        def installed = fileExists "${envDir}/bin/activate"

        checkout scm

        // Hard way of determining the Django settings path.
        // Might break if you have multiple directories in src
        if (!djangoSettings) {
            djangoSettings = sh(
                script: 'projectFolder=`cd src; ls -d */ | head -n 1`; echo "${projectFolder%?}.conf.jenkins"',
                returnStdout: true
            )
        }

        if (!installed) {
            sh "uv venv ${envDir}"
        }
    }

    stage ("Install backend requirements") {
        sh """
            . ${envDir}/bin/activate
            uv pip install pip --upgrade
            uv pip install -r requirements/ci.txt pytest-django pytest-cov
            deactivate
          """
    }

    stage ("Install frontend requirements") {
        sh """
            npm ci
            npm run build --production --sourcemap
           """

        withEnv(["SECRET_KEY=test_key"]) {
            sh """
                . ${envDir}/bin/activate
                python src/manage.py collectstatic \
                    --link \
                    --noinput \
                    --settings=${djangoSettings}
                deactivate
           """
        }
    }

    stage ("Test backend") {
        def testsError = null
        def keepDbOption = ""

        if (!env.CHANGE_TARGET) {
            keepDbOption = "--reuse-db"
        }

        withEnv(["SECRET_KEY=test_key","ELASTIC_APM_DISABLE_SEND=true"]) {
            try {
                sh """
                    . ${envDir}/bin/activate
                    pytest src \
                        --cov=src \
                        --cov-report=xml:${testCoverageFile}  \
                        --junit-xml=${testResultsFile} \
                        --verbosity 2 \
                        ${keepDbOption} \
                        --ds=${djangoSettings}
                    deactivate
                """
            }
            catch(err) {
                testsError = err
                currentBuild.result = "FAILURE"
            }
            finally {
                dir("media") {
                    deleteDir()
                }
                junit "reports/junit.xml"

                if (testsError) {
                    throw testsError
                }
            }
        }

        withEnv(["SECRET_KEY=test_key"]) {
            try {
                sh "${envDir}/bin/ruff check src --output-format pylint -o reports/pylint.report"
            }
            catch(err) {
                // Nothing...
            }
        }
    }

    stage ("Test frontend") {
        def testsError = null

        try {
            sh "xvfb-run -a --server-args='-screen 0, 1920x1200x16' npm test"
        }
        catch(err) {
            testsError = err
            currentBuild.result = "FAILURE"
        }
        finally {
            junit "${testResultsFile}"

            if (testsError) {
                throw testsError
            }
        }
    }

    stage ("Quality") {
        step(
            [
                $class: "CoberturaPublisher",
                coberturaReportFile: "reports/coverage.xml"
            ]
        )
        step(
            [
                $class: "WarningsPublisher",
                parserConfigurations: [
                    [
                        parserName: "PyLint",
                        pattern: "reports/pylint.report",
                        unstableTotalAll: "10",
                        usePreviousBuildAsReference: true,
                    ],
                ]
            ]
        )
    }
}
