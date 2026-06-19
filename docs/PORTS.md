# Port Registry

## River FIS

- Service: `River FIS`
- Default local host: `127.0.0.1`
- Default port: `61845`
- UI: `http://127.0.0.1:61845/`
- API base: `http://127.0.0.1:61845/api`
- Batch launcher: `start_fis.bat`
- Diagnostics: `troubleshoot_fis.bat`

## Notes

- This project uses a 5-digit port on purpose to avoid collisions with other local tools.
- Change the launcher default in `start_fis.bat` and `troubleshoot_fis.bat` if a different 5-digit port is needed later.
