test_file = open('tp_test', 'w')
for i in range(1000):
	if i % 2 == 0:
		test_file.write('begin add_book 123 Kenneth 40\n')
	else:
		tid = i/2+0.5
		test_file.write('commit t{}\n'.format(int(tid)))
test_file.close()