# Deployment Checklist

This project deploys as two services:

- Backend on Render: Flask/Gunicorn Docker web service from the repository root.
- Frontend on Vercel: Vite static site, built from the repository root by `vercel.json`.

## Render

Use the checked-in `render.yaml` blueprint or create a Docker web service manually. The backend must bind to `0.0.0.0` and the `PORT` environment variable; the Dockerfile already does this with Gunicorn. Render's default expected port is `10000`, and the service health check is `/api/health`.

Expected backend URL for the current service name:

`https://urbanheatai-backend.onrender.com`

After Render finishes, open:

`https://urbanheatai-backend.onrender.com/api/health`

You should see `status: ok`, `model_loaded: true`, `dataset_loaded: true`, and `raster_ready: true`.

## Vercel

Deploy from the repository root. The root `vercel.json` runs:

- Install: `npm --prefix frontend ci`
- Build: `npm --prefix frontend run build`
- Output: `frontend/dist`

Set this environment variable in Vercel Project Settings before the production build:

`VITE_API_URL=https://urbanheatai-backend.onrender.com`

The committed `frontend/.env.production` has the same default, but the Vercel dashboard value should be treated as the source of truth after you know the final Render URL.

## Required Files

These must be committed/pushed for Render to work:

- `backend/app.py`
- `backend/generate_raster.py`
- `backend/requirements.txt`
- `models/output/trained_model.pkl`
- `data/final/master_dataset.csv`
- `outputs/rasters/*.tif` or `data/raw/rasters/*.tif`

## Useful Official Docs

- Render web services and port binding: https://render.com/docs/web-services#port-binding
- Vercel Vite SPA rewrites: https://vercel.com/docs/frameworks/frontend/vite#using-vite-to-make-spas
- Vercel project configuration: https://vercel.com/docs/project-configuration
