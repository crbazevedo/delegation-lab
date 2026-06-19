/**
 * mso-registry.js — model cost + license registry for the allocation optimizer.
 *
 * GENERATED FROM src/minimal_oversight/data/model_registry.yaml — DO NOT EDIT.
 * Regenerate with:  python scripts/gen_registry_js.py
 *
 * cost = USD per million tokens (input/output). blended = 0.6*in + 0.4*out.
 * cost_index = 1..100 log-scale. open = open-weights AND commercially usable.
 * Provenance: docs/methodology/priors-evidence.md (GAP 6).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MSO_Registry = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MODELS = {
  "bge-m3": {provider:"baai",modality:"embedding",license:"MIT",open:true,input:0.02,output:0.0,blended:0.012,cost_index:1.0},
  "bge-reranker-v2-m3": {provider:"baai",modality:"reranker",license:"MIT",open:true,input:0.02,output:0.0,blended:0.012,cost_index:1.0},
  "claude-haiku-4": {provider:"anthropic",modality:"llm",license:"proprietary",open:false,input:1.0,output:5.0,blended:2.6,cost_index:56.0},
  "claude-opus-4": {provider:"anthropic",modality:"llm",license:"proprietary",open:false,input:15.0,output:75.0,blended:39.0,cost_index:94.0},
  "claude-opus-4.8": {provider:"anthropic",modality:"llm",license:"proprietary",open:false,input:5.0,output:25.0,blended:13.0,cost_index:79.0},
  "claude-sonnet-4": {provider:"anthropic",modality:"llm",license:"proprietary",open:false,input:3.0,output:15.0,blended:7.8,cost_index:72.0},
  "cohere-embed-v3": {provider:"cohere",modality:"embedding",license:"proprietary",open:false,input:0.1,output:0.0,blended:0.06,cost_index:4.0},
  "cohere-rerank-3": {provider:"cohere",modality:"reranker",license:"proprietary",open:false,input:0.2,output:0.0,blended:0.12,cost_index:13.0},
  "deepseek-r1": {provider:"deepseek",modality:"llm",license:"DeepSeek (MIT-style)",open:true,input:0.55,output:2.19,blended:1.206,cost_index:45.0},
  "deepseek-v3": {provider:"deepseek",modality:"llm",license:"DeepSeek (MIT-style)",open:true,input:0.27,output:1.1,blended:0.602,cost_index:36.0},
  "e5-mistral-7b": {provider:"open",modality:"embedding",license:"MIT",open:true,input:0.05,output:0.0,blended:0.03,cost_index:1.0},
  "fable-5": {provider:"unknown",modality:"llm",license:"proprietary",open:false,input:null,output:null,blended:null,cost_index:null},
  "gemini-2-flash": {provider:"google",modality:"llm",license:"proprietary",open:false,input:0.1,output:0.4,blended:0.22,cost_index:22.0},
  "gemini-2-pro": {provider:"google",modality:"llm",license:"proprietary",open:false,input:1.25,output:5.0,blended:2.75,cost_index:57.0},
  "gemini-2.5-flash-lite": {provider:"google",modality:"llm",license:"proprietary",open:false,input:0.1,output:0.4,blended:0.22,cost_index:22.0},
  "gemini-2.5-pro": {provider:"google",modality:"llm",license:"proprietary",open:false,input:1.25,output:10.0,blended:4.75,cost_index:65.0},
  "gpt-4o": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:2.5,output:10.0,blended:5.5,cost_index:67.0},
  "gpt-4o-mini": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:0.15,output:0.6,blended:0.33,cost_index:27.0},
  "gpt-5.4-nano": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:0.2,output:1.25,blended:0.62,cost_index:36.0},
  "gpt-5.5": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:5.0,output:30.0,blended:15.0,cost_index:81.0},
  "granite-embedding-r2": {provider:"ibm",modality:"embedding",license:"Apache-2.0",open:true,input:0.02,output:0.0,blended:0.012,cost_index:1.0},
  "kimi-2.6": {provider:"moonshot",modality:"llm",license:"Modified-MIT",open:true,input:0.6,output:2.5,blended:1.36,cost_index:47.0},
  "kimi-k2.5": {provider:"moonshot",modality:"llm",license:"Modified-MIT",open:true,input:0.6,output:2.5,blended:1.36,cost_index:47.0},
  "llama-3.3-70b": {provider:"meta",modality:"llm",license:"Llama-Community",open:true,input:0.88,output:0.88,blended:0.88,cost_index:41.0},
  "mistral-large": {provider:"mistral",modality:"llm",license:"MRL (research-only)",open:false,input:2.0,output:6.0,blended:3.6,cost_index:61.0},
  "o3-pro": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:20.0,output:80.0,blended:44.0,cost_index:96.0},
  "o4-mini-high": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:1.1,output:4.4,blended:2.42,cost_index:55.0},
  "openai-o3": {provider:"openai",modality:"llm",license:"proprietary",open:false,input:2.0,output:8.0,blended:4.4,cost_index:64.0},
  "openai-text-embedding-3-large": {provider:"openai",modality:"embedding",license:"proprietary",open:false,input:0.13,output:0.0,blended:0.078,cost_index:7.0},
  "openai-text-embedding-3-small": {provider:"openai",modality:"embedding",license:"proprietary",open:false,input:0.02,output:0.0,blended:0.012,cost_index:1.0},
  "phi-4": {provider:"microsoft",modality:"llm",license:"MIT",open:true,input:0.07,output:0.14,blended:0.098,cost_index:10.0},
  "qwen2.5-72b": {provider:"alibaba",modality:"llm",license:"Qwen (Apache-2.0)",open:true,input:0.4,output:0.4,blended:0.4,cost_index:30.0},
  "qwen3-8b": {provider:"alibaba",modality:"llm",license:"Apache-2.0",open:true,input:0.1,output:0.2,blended:0.14,cost_index:15.0},
  "qwen3-embedding-8b": {provider:"alibaba",modality:"embedding",license:"Apache-2.0",open:true,input:0.05,output:0.0,blended:0.03,cost_index:1.0},
  "qwen3-reranker": {provider:"alibaba",modality:"reranker",license:"Apache-2.0",open:true,input:0.05,output:0.0,blended:0.03,cost_index:1.0},
  "rankgpt-gpt4": {provider:"openai",modality:"reranker",license:"proprietary",open:false,input:10.0,output:30.0,blended:18.0,cost_index:83.0},
  "rankzephyr-7b": {provider:"open",modality:"reranker",license:"research",open:false,input:0.05,output:0.0,blended:0.03,cost_index:1.0},
  };

  function has(name) { return !!MODELS[name]; }
  function get(name) { return MODELS[name] || null; }
  function listModels() { return Object.keys(MODELS).sort(); }
  function isOpenSource(name) { var m = MODELS[name]; return !!(m && m.open); }
  function blendedCost(name) { var m = MODELS[name]; return m ? m.blended : null; }
  function costIndex(name) { var m = MODELS[name]; return m ? m.cost_index : null; }

  // USD per invocation given token volumes. null for an unpriced model.
  function costPerRun(name, inputTokens, outputTokens) {
    var m = MODELS[name];
    if (!m || m.input == null || m.output == null) return null;
    outputTokens = outputTokens || 0;
    return (inputTokens * m.input + outputTokens * m.output) / 1000000.0;
  }

  function modelsByModality(modality) {
    return Object.keys(MODELS).filter(function (n) {
      return MODELS[n].modality === modality;
    }).sort();
  }

  function openModels() {
    return Object.keys(MODELS).filter(function (n) { return MODELS[n].open; }).sort();
  }

  return {
    has: has, get: get, listModels: listModels, isOpenSource: isOpenSource,
    blendedCost: blendedCost, costIndex: costIndex, costPerRun: costPerRun,
    modelsByModality: modelsByModality, openModels: openModels
  };
});
