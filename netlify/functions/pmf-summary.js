import { requireAuth, corsHeaders } from './utils.js';
import fs from 'fs';
import path from 'path';

export default async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders()
    });
  }

  if (req.method !== 'GET') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: corsHeaders()
    });
  }

  const auth = requireAuth(req);
  if (auth.error) {
    return new Response(JSON.stringify({ error: auth.error }), {
      status: auth.status,
      headers: corsHeaders()
    });
  }

  try {
    const jsonPath = path.join(process.cwd(), 'backend', 'output', 'agent4_summary.json');

    if (!fs.existsSync(jsonPath)) {
      return new Response(
        JSON.stringify({ error: 'No summary available' }),
        { status: 404, headers: corsHeaders() }
      );
    }

    const summary = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));

    return new Response(
      JSON.stringify({
        status: 'success',
        data: summary
      }),
      { status: 200, headers: corsHeaders() }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: corsHeaders() }
    );
  }
};
