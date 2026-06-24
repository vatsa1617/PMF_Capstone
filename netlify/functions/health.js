import { corsHeaders } from './utils.js';

export default async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders()
    });
  }

  return new Response(
    JSON.stringify({ status: 'ok' }),
    { status: 200, headers: corsHeaders() }
  );
};
