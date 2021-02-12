pragma solidity >=0.8.1 <0.9;

library WBytes32Set {

    struct Data {
        bytes32 data;
        uint8 weight;
    }

	struct Set {
		mapping(bytes32 => uint) map;
		Data[] list;
	}

	function insert(Set storage self, bytes32 _data, uint8 _weight) internal returns(bool) {
		uint pointer = self.map[_data];

		if(pointer != 0) {
		    Data storage entry = self.list[pointer - 1];
		    
			if(entry.weight < _weight) {
				entry.weight = _weight;
				return true;
			}
			else
				return false;
		}

		self.list.push(Data(_data, _weight));
		pointer = size(self);
		self.map[_data] = pointer;
		return true;
	}

	function update(Set storage self, bytes32 _data, uint8 _weight) internal {
		uint pointer = self.map[_data];
		require(pointer != 0, "entry not found");

		self.list[pointer - 1].weight = _weight;
	}

	function remove(Set storage self, bytes32 _data) internal {
		uint pointerToRemove = self.map[_data];
		require(pointerToRemove != 0, "entry not found");
		uint lastPointer = size(self);

		if(pointerToRemove != lastPointer) {
			Data storage lastEntry = self.list[lastPointer - 1];
			self.list[pointerToRemove - 1] = lastEntry;
			self.map[lastEntry.data] = pointerToRemove;
		}
		self.list.pop();
		self.map[_data] = 0;
	}

	function size(Set storage self) internal view returns(uint) {
		return self.list.length;
	}

	function exists(Set storage self, bytes32 _data) internal view returns(bool) {
		uint pointer = self.map[_data];
		return pointer != 0;
	}

	function getPointer(Set storage self, bytes32 _data) internal view returns(uint) {
		return self.map[_data];
	}

	function getWeight(Set storage self, uint _index) internal view returns(uint8) {
		return self.list[_index].weight;
	}

	function get(Set storage self, uint _index) internal view returns(bytes32, uint8) {
		Data storage entry = self.list[_index];
        return (entry.data, entry.weight);
	}

}
