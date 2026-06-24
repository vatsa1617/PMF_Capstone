import { requireAuth, corsHeaders } from './utils.js';
import fs from 'fs';
import path from 'path';
import csv from 'csv-parse/sync';

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
    const csvPath = path.join(process.cwd(), 'backend', 'output', 'agent4_pmf_matrix.csv');

    if (!fs.existsSync(csvPath)) {
      return new Response(
        JSON.stringify({ error: 'No PMF data available. Run agent4.py first.' }),
        { status: 404, headers: corsHeaders() }
      );
    }

    const fileContent = fs.readFileSync(csvPath, 'utf-8');
    const records = csv.parse(fileContent, {
      columns: true,
      skip_empty_lines: true
    });

    const data = records.map(record => ({
      market: record.Market || record.market,
      technology: record.Technology || record.technology,
      pmf: parseFloat(record.PMF_Score || record.pmf),
      confidence: parseFloat(record.Confidence_Score || record.confidence),
      desirability: parseFloat(record.Desirability || record.desirability),
      feasibility: parseFloat(record.Feasibility || record.feasibility),
      viability: parseFloat(record.Viability || record.viability),
      risk: parseFloat(record.Risk_Penalty || record.risk)
    }));

    return new Response(
      JSON.stringify({
        status: 'success',
        data,
        count: data.length
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
