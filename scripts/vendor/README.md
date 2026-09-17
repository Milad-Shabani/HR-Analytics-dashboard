# Vendored libraries

These are unmodified redistributions of two open-source libraries, kept
here so the dashboard can be built and embedded fully offline (no CDN
dependency at build time or runtime):

- `chart.umd.js` — [Chart.js](https://www.chartjs.org/) v4.4.4, MIT License
- `xlsx.full.min.js` — [SheetJS](https://sheetjs.com/) (xlsx) v0.18.5, Apache-2.0 License

`scripts/export_dashboard_data.py` inlines both files directly into
`dashboard/index.html` at build time, alongside the workbook data, so the
final dashboard has zero external network dependencies -- it works even
on networks where CDNs like cdnjs.cloudflare.com are blocked or filtered.
