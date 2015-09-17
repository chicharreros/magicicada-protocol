:: Copyright 2012 Canonical Ltd.
::
:: This program is free software: you can redistribute it and/or modify it
:: under the terms of the GNU General Public License version 3, as published
:: by the Free Software Foundation.
::
:: This program is distributed in the hope that it will be useful, but
:: WITHOUT ANY WARRANTY; without even the implied warranties of
:: MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
:: PURPOSE.  See the GNU General Public License for more details.
::
:: You should have received a copy of the GNU General Public License along
:: with this program.  If not, see <http://www.gnu.org/licenses/>.

@ECHO off

SET MODULE="tests"
SET PYTHONEXEPATH=""
SET IGNORE_PATHS="ubuntuone\controlpanel\dbustests"
SET IGNORE_MODULES="test_linux.py, test_darwin.py"
SET PYTHONPATH=%PYTHONPATH%;..\ubuntu-sso-client;..\ubuntuone-dev-tools\;..\dirspec;.

ECHO Checking for Python on the path
:: Look for Python from buildout
FOR %%A in (python.exe) do (SET PYTHONEXEPATH=%%~$PATH:A)
FOR %%B in (u1trial) do (SET TRIALPATH=%%~$PATH:B)
FOR %%C in (u1lint) do (SET LINTPATH=%%~$PATH:C)
FOR %%D in (pep8.exe) do (SET PEP8PATH=%%~$PATH:D)

IF NOT "%PYTHONEXEPATH%" == "" GOTO :PYTHONPRESENT
ECHO Please ensure you have python installed
GOTO :END

:PYTHONPRESENT

:: throw the first parameter away if is /skip-lint,
:: the way we do this is to ensure that /skip-lint
:: is the first parameter and copy all the rest in a loop
:: the main reason for that is that %* is not affected
:: by SHIFT, that is, it allways have all passed parameters

SET PARAMS=%*
SET SKIPLINT=0
IF "%1" == "/skip-lint" (
    SET SKIPLINT=1
    GOTO :CLEANPARAMS
)ELSE (
    GOTO :CONTINUEBATCH) 
:CLEANPARAMS

SHIFT
SET PARAMS=%1
:GETREST
SHIFT
if [%1]==[] (
    GOTO CONTINUEBATCH)
SET PARAMS=%PARAMS% %1
GOTO GETREST
:CONTINUEBATCH


"%PYTHONEXEPATH%" setup.py build
ECHO Running tests
:: execute the tests with a number of ignored linux only modules
"%PYTHONEXEPATH%" "%TRIALPATH%" -p %IGNORE_PATHS% -i %IGNORE_MODULES% %PARAMS% %MODULE%

:: Clean the build from the setup.py
ECHO Cleaning the generated code
"%PYTHONEXEPATH%" setup.py clean

IF %SKIPLINT% == 1 GOTO :CLEAN
ECHO Performing style checks...
SET USE_PYFLAKES=1
"%PYTHONEXEPATH%" "%LINTPATH%" "%MODULE%"
"%PEP8PATH%" --exclude ".svn,CVS,.bzr,.hg,.git,*_ui.py,*_rc.py,*_pb2.py" --repeat .

:CLEAN
:: Delete the temp folders
IF "%TRIAL_TEMP_DIR%" == "" GOTO :TRIALTEMPEXISTS
IF EXIST _trial_temp RMDIR /s /q _trial_temp
:TRIALTEMPEXISTS
IF EXIST "%TRIAL_TEMP_DIR%" RMDIR /s /q "%TRIAL_TEMP_DIR%"
