import api from "./axiosConfig";

export const getBharathiDashboard = () => api.get("/bharathi/dashboard");
export const listBharathiBills = (params) => api.get("/bharathi/bills", { params });
export const createBharathiBill = (payload) => api.post("/bharathi/bills", payload);
export const submitBharathiBill = (id) => api.post(`/bharathi/bills/${id}/submit`);
export const verifyBharathiBill = (id, payload) => api.post(`/bharathi/bills/${id}/verify`, payload);
export const getCollectionsOutstanding = () => api.get("/bharathi/collections/outstanding");
export const runTallySync = (payload) => api.post("/bharathi/tally/sync", payload);