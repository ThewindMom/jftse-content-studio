-- jftse-content-studio item pack
-- product index 271 mesh 271
INSERT INTO S_Product (`index`, name, part, mesh, tex, effect, gold) VALUES (271, 'Part injection live HTTP', 'Racket'', 0, 0, 0, 0); INSERT INTO S_Maps (id) VALUES (424242); --', 271, 0, 0, 0) ON DUPLICATE KEY UPDATE name=VALUES(name), part=VALUES(part), mesh=VALUES(mesh), tex=VALUES(tex), effect=VALUES(effect), gold=VALUES(gold);
INSERT INTO product (`index`, name, part, mesh, tex, effect, gold) VALUES (271, 'Part injection live HTTP', 'Racket'', 0, 0, 0, 0); INSERT INTO S_Maps (id) VALUES (424242); --', 271, 0, 0, 0) ON DUPLICATE KEY UPDATE name=VALUES(name), mesh=VALUES(mesh);
