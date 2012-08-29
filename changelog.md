Python Impact Web Server Changelog
==================================

# v1.1.1
- Added Windows file structure fixes to browse() and glob() so that Weltmeister would load properly
- Added initial print message to reflect the changes added to the main repo.


# v1.1
- Fixed MIME requests so that the data is explicitly opened in binary mode. This is due to Windows treating text and binary files differently.
- Updated source from Python 2.x to 3.x